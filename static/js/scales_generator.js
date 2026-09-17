/**
 * Scale Texture Generator Web Engine (KurilenkoArt)
 * High-performance procedural heightmap generator for 3D sculpting.
 * Supports PNG 8-bit / 16-bit Grayscale and 32-bit Float TIFF (.tif).
 */

(function () {
    'use strict';

    // --- 1. Monotone Cubic Spline (Fritsch-Carlson) ---
    function evaluateCurve(x, points) {
        if (!points || points.length === 0) return x;
        if (points.length === 1) return Math.max(0, Math.min(1, points[0].y));

        const p = points.slice().sort((a, b) => a.x - b.x);
        const n = p.length;

        if (x <= p[0].x) return Math.max(0, Math.min(1, p[0].y));
        if (x >= p[n - 1].x) return Math.max(0, Math.min(1, p[n - 1].y));

        let i = 0;
        while (i < n - 2 && x > p[i + 1].x) i++;

        const x0 = p[i].x, y0 = p[i].y;
        const x1 = p[i + 1].x, y1 = p[i + 1].y;
        const h = x1 - x0;
        if (h <= 1e-9) return y0;

        const m = new Float64Array(n - 1);
        for (let k = 0; k < n - 1; k++) {
            const dx = p[k + 1].x - p[k].x;
            m[k] = dx > 1e-9 ? (p[k + 1].y - p[k].y) / dx : 0;
        }

        const d = new Float64Array(n);
        d[0] = m[0];
        d[n - 1] = m[n - 2];
        for (let k = 1; k < n - 1; k++) {
            if (m[k - 1] * m[k] <= 0) {
                d[k] = 0;
            } else {
                d[k] = (2.0 * m[k - 1] * m[k]) / (m[k - 1] + m[k]);
            }
        }

        const t = (x - x0) / h;
        const t2 = t * t;
        const t3 = t2 * t;

        const h00 = 2 * t3 - 3 * t2 + 1;
        const h10 = t3 - 2 * t2 + t;
        const h01 = -2 * t3 + 3 * t2;
        const h11 = t3 - t2;

        const val = h00 * y0 + h10 * h * d[i] + h01 * y1 + h11 * h * d[i + 1];
        return Math.max(0, Math.min(1, val));
    }

    // --- 2. Procedural Scale Pattern Height Engine ---
    function getScaleHeight(u, v, s) {
        let a = u, b = v;
        if (s.direction === 1) a = 1 - u;
        if (s.direction === 2) { a = v; b = 1 - u; }
        if (s.direction === 3) { a = 1 - v; b = u; }

        a -= Math.floor(a);
        b -= Math.floor(b);

        const effectiveRows = (s.stagger > 0 && (s.rows % 2 !== 0)) ? s.rows + 1 : s.rows;
        const x = a * s.columns;
        const y = b * effectiveRows;

        const length = 1.0 / (1.0 - s.overlap);
        let value = 0.0;

        const row0 = Math.floor(y);
        const range = Math.ceil(length) + 1;

        for (let row = row0 - 1; row <= row0 + 1; row++) {
            const dy = Math.abs(y - (row + 0.5));
            const offset = ((row % 2 + 2) % 2) * s.stagger;
            const col0 = Math.floor(x - offset);

            for (let col = col0 - range; col <= col0 + 1; col++) {
                const t = (x - (col + offset)) / length;
                if (t < 0 || t > 1) continue;

                let boundary = 0;
                if (s.shape === 0) {
                    boundary = 1.0 - Math.abs(2 * t - 1.0);
                } else if (s.shape === 1) {
                    boundary = Math.sqrt(Math.max(0, 1.0 - (2 * t - 1.0) * (2 * t - 1.0))) * 0.95;
                } else if (s.shape === 2) {
                    const cap = Math.min(0.48, 0.5 / length);
                    boundary = t < 1 - cap ? 0.5 : 0.5 * Math.sqrt(Math.max(0, 1.0 - Math.pow((t - (1 - cap)) / cap, 2)));
                } else {
                    const cap = 0.55;
                    boundary = t < 1 - cap ? 0.9 : 0.9 * Math.sqrt(Math.max(0, 1.0 - Math.pow((t - (1 - cap)) / cap, 2)));
                }

                if (dy > boundary) continue;
                if (t > value) value = t;
            }
        }

        value = Math.pow(value, s.gamma);
        value = evaluateCurve(value, s.curvePoints);
        value = s.minimum + (s.maximum - s.minimum) * value;

        return s.invert ? 1.0 - value : value;
    }

    function getPixelHeight(x, y, w, h, s, aa) {
        if (!aa || aa <= 1) {
            return getScaleHeight((x + 0.5) / w, (y + 0.5) / h, s);
        }
        let sum = 0.0;
        for (let j = 0; j < aa; j++) {
            for (let i = 0; i < aa; i++) {
                const u = (x + (i + 0.5) / aa) / w;
                const v = (y + (j + 0.5) / aa) / h;
                sum += getScaleHeight(u, v, s);
            }
        }
        return sum / (aa * aa);
    }

    // --- 3. Interactive Spline Curve Control ---
    class SplineCurveEditor {
        constructor(canvas, onChange) {
            this.canvas = canvas;
            this.ctx = canvas.getContext('2d');
            this.onChange = onChange;
            this.points = [{ x: 0, y: 0 }, { x: 1, y: 1 }];
            this.draggedIndex = -1;
            this.hoverIndex = -1;

            this.initEvents();
            this.draw();
        }

        getPlotArea() {
            return {
                left: 14,
                top: 14,
                width: this.canvas.width - 28,
                height: this.canvas.height - 28,
                bottom: this.canvas.height - 14,
                right: this.canvas.width - 14
            };
        }

        valToClient(pt) {
            const plot = this.getPlotArea();
            return {
                x: plot.left + pt.x * plot.width,
                y: plot.bottom - pt.y * plot.height
            };
        }

        clientToVal(pt) {
            const plot = this.getPlotArea();
            return {
                x: Math.max(0, Math.min(1, (pt.x - plot.left) / plot.width)),
                y: Math.max(0, Math.min(1, (plot.bottom - pt.y) / plot.height))
            };
        }

        resetLinear() {
            this.setPoints([{ x: 0, y: 0 }, { x: 1, y: 1 }]);
        }

        setSCurve() {
            this.setPoints([{ x: 0, y: 0 }, { x: 0.25, y: 0.08 }, { x: 0.75, y: 0.92 }, { x: 1, y: 1 }]);
        }

        setConcave() {
            this.setPoints([{ x: 0, y: 0 }, { x: 0.5, y: 0.15 }, { x: 1, y: 1 }]);
        }

        setConvex() {
            this.setPoints([{ x: 0, y: 0 }, { x: 0.5, y: 0.85 }, { x: 1, y: 1 }]);
        }

        setPoints(pts) {
            this.points = pts.slice().sort((a, b) => a.x - b.x);
            this.draw();
            if (this.onChange) this.onChange();
        }

        draw() {
            const ctx = this.ctx;
            const w = this.canvas.width;
            const h = this.canvas.height;
            const plot = this.getPlotArea();

            ctx.clearRect(0, 0, w, h);

            // Solid dark background for crisp high contrast
            ctx.fillStyle = '#12161f';
            ctx.fillRect(0, 0, w, h);

            // Grid lines (faint green dash)
            ctx.strokeStyle = 'rgba(61, 122, 79, 0.35)';
            ctx.setLineDash([3, 3]);
            for (let i = 1; i <= 3; i++) {
                const gx = plot.left + (plot.width * i) / 4;
                const gy = plot.top + (plot.height * i) / 4;
                ctx.beginPath(); ctx.moveTo(gx, plot.top); ctx.lineTo(gx, plot.bottom); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(plot.left, gy); ctx.lineTo(plot.right, gy); ctx.stroke();
            }

            // Diagonal reference line (faint green dot)
            ctx.strokeStyle = 'rgba(61, 122, 79, 0.5)';
            ctx.setLineDash([2, 2]);
            ctx.beginPath();
            ctx.moveTo(plot.left, plot.bottom);
            ctx.lineTo(plot.right, plot.top);
            ctx.stroke();
            ctx.setLineDash([]);

            // Plot outline (Dark Green)
            ctx.strokeStyle = '#3d7a4f';
            ctx.lineWidth = 1.5;
            ctx.strokeRect(plot.left, plot.top, plot.width, plot.height);

            // Curve line (Bright Mint #00f0a8, 3px thick)
            if (this.points && this.points.length >= 2) {
                ctx.beginPath();
                ctx.strokeStyle = '#00f0a8';
                ctx.lineWidth = 3;

                for (let px = 0; px <= plot.width; px++) {
                    const vx = px / plot.width;
                    const vy = evaluateCurve(vx, this.points);
                    const client = this.valToClient({ x: vx, y: vy });
                    if (px === 0) ctx.moveTo(client.x, client.y);
                    else ctx.lineTo(client.x, client.y);
                }
                ctx.stroke();
            }

            // Control points handles
            for (let i = 0; i < this.points.length; i++) {
                const cp = this.valToClient(this.points[i]);
                const isHover = (i === this.hoverIndex || i === this.draggedIndex);
                const r = isHover ? 7 : 5;

                ctx.fillStyle = '#ffffff';
                ctx.beginPath();
                ctx.arc(cp.x, cp.y, r, 0, Math.PI * 2);
                ctx.fill();

                ctx.strokeStyle = isHover ? '#00f0a8' : '#3d7a4f';
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            // Tooltip text
            if (this.hoverIndex >= 0 && this.hoverIndex < this.points.length) {
                const pt = this.points[this.hoverIndex];
                ctx.fillStyle = '#00f0a8';
                ctx.font = 'bold 11px "Segoe UI", sans-serif';
                ctx.fillText(`X: ${pt.x.toFixed(2)}, Y: ${pt.y.toFixed(2)}`, plot.left + 6, plot.top + 14);
            }
        }

        getMousePos(e) {
            const rect = this.canvas.getBoundingClientRect();
            return {
                x: (e.clientX - rect.left) * (this.canvas.width / rect.width),
                y: (e.clientY - rect.top) * (this.canvas.height / rect.height)
            };
        }

        hitTest(pos) {
            for (let i = 0; i < this.points.length; i++) {
                const cp = this.valToClient(this.points[i]);
                const dx = pos.x - cp.x;
                const dy = pos.y - cp.y;
                if (dx * dx + dy * dy <= 12 * 12) return i;
            }
            return -1;
        }

        initEvents() {
            this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());

            this.canvas.addEventListener('mousedown', (e) => {
                const pos = this.getMousePos(e);

                if (e.button === 2) { // Right click delete
                    const idx = this.hitTest(pos);
                    if (idx > 0 && idx < this.points.length - 1) {
                        this.points.splice(idx, 1);
                        this.points.sort((a, b) => a.x - b.x);
                        this.draw();
                        if (this.onChange) this.onChange();
                    }
                    return;
                }

                if (e.button === 0) { // Left click
                    let idx = this.hitTest(pos);
                    if (idx >= 0) {
                        this.draggedIndex = idx;
                    } else {
                        const val = this.clientToVal(pos);
                        this.points.push(val);
                        this.points.sort((a, b) => a.x - b.x);
                        this.draggedIndex = this.points.findIndex(p => p.x === val.x && p.y === val.y);
                        this.draw();
                        if (this.onChange) this.onChange();
                    }
                }
            });

            window.addEventListener('mousemove', (e) => {
                if (this.draggedIndex >= 0) {
                    const pos = this.getMousePos(e);
                    let val = this.clientToVal(pos);

                    if (this.draggedIndex === 0) {
                        val.x = 0;
                    } else if (this.draggedIndex === this.points.length - 1) {
                        val.x = 1;
                    } else {
                        const minX = this.points[this.draggedIndex - 1].x + 0.02;
                        const maxX = this.points[this.draggedIndex + 1].x - 0.02;
                        val.x = Math.max(minX, Math.min(maxX, val.x));
                    }

                    this.points[this.draggedIndex] = val;
                    this.hoverIndex = this.draggedIndex;
                    this.draw();
                    if (this.onChange) this.onChange();
                } else {
                    const pos = this.getMousePos(e);
                    const oldHover = this.hoverIndex;
                    this.hoverIndex = this.hitTest(pos);
                    if (oldHover !== this.hoverIndex) this.draw();
                }
            });

            window.addEventListener('mouseup', () => {
                if (this.draggedIndex >= 0) {
                    this.draggedIndex = -1;
                    this.draw();
                }
            });
        }
    }

    // --- 4. Main Web Application State & Controller ---
    let curveEditor = null;
    let renderTimer = null;

    function getSettingsFromUI() {
        const shapeEl = document.getElementById('shape');
        const directionEl = document.getElementById('direction');
        const widthEl = document.getElementById('width');
        const heightEl = document.getElementById('height');
        const columnsEl = document.getElementById('columns');
        const rowsEl = document.getElementById('rows');
        const overlapEl = document.getElementById('overlap');
        const staggerEl = document.getElementById('stagger');
        const gammaEl = document.getElementById('gamma');
        const minEl = document.getElementById('minimum');
        const maxEl = document.getElementById('maximum');
        const invertEl = document.getElementById('invert');
        const depthEl = document.getElementById('depth');
        const tilesEl = document.getElementById('tiles');
        const smoothEl = document.getElementById('smooth');

        const shape = shapeEl ? parseInt(shapeEl.value) || 0 : 0;
        const direction = directionEl ? parseInt(directionEl.value) || 0 : 0;
        const width = Math.max(64, Math.min(8000, parseInt(widthEl ? widthEl.value : 2048) || 2048));
        const height = Math.max(64, Math.min(8000, parseInt(heightEl ? heightEl.value : 1024) || 1024));
        const columns = parseInt(columnsEl ? columnsEl.value : 20) || 20;
        const rows = parseInt(rowsEl ? rowsEl.value : 24) || 24;
        const overlap = (parseFloat(overlapEl ? overlapEl.value : 15) || 15) / 100.0;
        const stagger = (parseFloat(staggerEl ? staggerEl.value : 50) || 50) / 100.0;
        const gamma = (parseFloat(gammaEl ? gammaEl.value : 100) || 100) / 100.0;
        const minimum = (parseFloat(minEl ? minEl.value : 0) || 0) / 100.0;
        const maximum = (parseFloat(maxEl ? maxEl.value : 100) || 100) / 100.0;
        const invert = invertEl ? invertEl.checked : false;
        const depth = parseInt(depthEl ? depthEl.value : 0) || 0;
        const tiled = tilesEl ? tilesEl.checked : false;
        const smooth = smoothEl ? smoothEl.checked : false;

        let bits = 16;
        if (depth === 1) bits = 8;
        if (depth === 2) bits = 32;

        return {
            shape, direction, width, height, columns, rows,
            overlap, stagger, gamma, minimum, maximum, invert,
            bits, tiled, smooth,
            curvePoints: curveEditor ? curveEditor.points : [{ x: 0, y: 0 }, { x: 1, y: 1 }]
        };
    }

    function scheduleRender() {
        if (renderTimer) clearTimeout(renderTimer);
        renderTimer = setTimeout(renderPreview, 50);
    }

    function resetTemplateDefaults() {
        const shapeSelect = document.getElementById('shape');
        const shape = parseInt(shapeSelect ? shapeSelect.value : 0) || 0;

        if (document.getElementById('direction')) document.getElementById('direction').value = '0';
        if (document.getElementById('width')) document.getElementById('width').value = '2048';
        if (document.getElementById('height')) document.getElementById('height').value = '1024';
        if (document.getElementById('columns')) document.getElementById('columns').value = '20';
        if (document.getElementById('rows')) document.getElementById('rows').value = '24';

        if (document.getElementById('stagger') && document.getElementById('overlap')) {
            if (shape === 2) {
                document.getElementById('stagger').value = '0';
                document.getElementById('overlap').value = '15';
            } else if (shape === 0) {
                document.getElementById('stagger').value = '50';
                document.getElementById('overlap').value = '0';
            } else {
                document.getElementById('stagger').value = '50';
                document.getElementById('overlap').value = '15';
            }
            if (document.getElementById('overlapVal')) document.getElementById('overlapVal').textContent = document.getElementById('overlap').value + '%';
            if (document.getElementById('staggerVal')) document.getElementById('staggerVal').textContent = document.getElementById('stagger').value + '%';
        }

        if (document.getElementById('gamma')) {
            document.getElementById('gamma').value = '100';
            if (document.getElementById('gammaVal')) document.getElementById('gammaVal').textContent = '100%';
        }
        if (document.getElementById('minimum')) {
            document.getElementById('minimum').value = '0';
            if (document.getElementById('minVal')) document.getElementById('minVal').textContent = '0%';
        }
        if (document.getElementById('maximum')) {
            document.getElementById('maximum').value = '100';
            if (document.getElementById('maxVal')) document.getElementById('maxVal').textContent = '100%';
        }
        if (document.getElementById('invert')) document.getElementById('invert').checked = false;
        if (document.getElementById('depth')) document.getElementById('depth').value = '0';

        if (curveEditor) curveEditor.resetLinear();

        scheduleRender();
    }

    function renderPreview() {
        const canvas = document.getElementById('previewCanvas');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const s = getSettingsFromUI();

        // Calculate preview aspect ratio fit
        const containerWidth = canvas.parentElement ? Math.max(300, Math.min(800, canvas.parentElement.clientWidth - 32)) : 600;
        let w = containerWidth;
        let h = Math.round(w * (s.height / s.width));
        if (h > 450) {
            h = 450;
            w = Math.round(h * (s.width / s.height));
        }

        canvas.width = w;
        canvas.height = h;

        const imgData = ctx.createImageData(w, h);
        const data = imgData.data;

        const tiled = s.tiled;
        const aa = s.smooth ? 2 : 1;

        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                let val;
                if (tiled) {
                    const u = ((x + 0.5) * 2 / w) % 1.0;
                    const v = ((y + 0.5) * 2 / h) % 1.0;
                    val = getScaleHeight(u, v, s);
                } else {
                    val = getPixelHeight(x, y, w, h, s, aa);
                }

                const c = Math.round(val * 255);
                const p = (y * w + x) * 4;
                data[p] = c;
                data[p + 1] = c;
                data[p + 2] = c;
                data[p + 3] = 255;
            }
        }

        ctx.putImageData(imgData, 0, 0);

        const dimsLabel = document.getElementById('dimensionsInfo');
        if (dimsLabel) {
            const isEn = (document.documentElement.getAttribute('lang') === 'en') || (localStorage.getItem('lang') === 'en');
            const effRows = (s.stagger > 0 && (s.rows % 2 !== 0)) ? s.rows + 1 : s.rows;
            const repeatsWord = isEn ? 'repeats' : 'повторов';
            const roundedNote = isEn ? ' (rows rounded up to even count)' : ' (ряды округлены до чётного числа)';
            dimsLabel.textContent = `${s.width} × ${s.height} px  ·  ${s.columns} × ${effRows} ${repeatsWord}` +
                (s.rows !== effRows ? roundedNote : '');
        }
    }

    // --- 5. Export Encoders: 32-bit Float TIFF & 16-bit / 8-bit PNG ---
    function saveTiff32Float(s, progressCb) {
        const w = s.width;
        const h = s.height;
        const aa = s.smooth ? 2 : 1;

        const headerSize = 8;
        const softStr = "Scale Texture Generator 1.1 (32-bit Float Heightmap)\0";
        const softBytes = new TextEncoder().encode(softStr);

        const ifdNumEntries = 15;
        const ifdSize = 2 + ifdNumEntries * 12 + 4;

        const softOffset = headerSize + ifdSize;
        const xResOffset = softOffset + softBytes.length;
        const yResOffset = xResOffset + 8;
        let pixelOffset = yResOffset + 8;
        if ((pixelOffset & 1) !== 0) pixelOffset++;

        const pixelDataSize = w * h * 4;
        const totalSize = pixelOffset + pixelDataSize;

        const buffer = new ArrayBuffer(totalSize);
        const view = new DataView(buffer);

        // Header: Little Endian 'II'
        view.setUint8(0, 0x49); view.setUint8(1, 0x49);
        view.setUint16(2, 42, true);
        view.setUint32(4, 8, true);

        // IFD
        let offset = 8;
        view.setUint16(offset, ifdNumEntries, true); offset += 2;

        function writeTag(tag, type, count, val) {
            view.setUint16(offset, tag, true);
            view.setUint16(offset + 2, type, true);
            view.setUint32(offset + 4, count, true);
            view.setUint32(offset + 8, val, true);
            offset += 12;
        }

        // Tags strictly sorted in ascending order for Adobe libtiff compliance
        writeTag(256, 4, 1, w);                               // ImageWidth
        writeTag(257, 4, 1, h);                               // ImageLength
        writeTag(258, 3, 1, 32);                              // BitsPerSample = 32
        writeTag(259, 3, 1, 1);                               // Compression = None
        writeTag(262, 3, 1, 1);                               // Photometric = BlackIsZero
        writeTag(273, 4, 1, pixelOffset);                     // StripOffsets
        writeTag(277, 3, 1, 1);                               // SamplesPerPixel = 1
        writeTag(278, 4, 1, h);                               // RowsPerStrip
        writeTag(279, 4, 1, pixelDataSize);                   // StripByteCounts
        writeTag(282, 5, 1, xResOffset);                      // XResolution (Rational)
        writeTag(283, 5, 1, yResOffset);                      // YResolution (Rational)
        writeTag(284, 3, 1, 1);                               // PlanarConfiguration = 1 (Chunky)
        writeTag(296, 3, 1, 2);                               // ResolutionUnit = 2 (Inches)
        writeTag(305, 2, softBytes.length, softOffset);        // Software
        writeTag(339, 3, 1, 3);                               // SampleFormat = IEEE Float

        view.setUint32(offset, 0, true);                      // Next IFD = 0

        // Write software string bytes
        const byteArr = new Uint8Array(buffer);
        byteArr.set(softBytes, softOffset);

        // Write Resolution Rationals (72 / 1)
        view.setUint32(xResOffset, 72, true);
        view.setUint32(xResOffset + 4, 1, true);
        view.setUint32(yResOffset, 72, true);
        view.setUint32(yResOffset + 4, 1, true);

        // Write 32-bit Float Pixel Data
        let floatOffset = pixelOffset;
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const val = getPixelHeight(x, y, w, h, s, aa);
                view.setFloat32(floatOffset, val, true); // Little endian float32
                floatOffset += 4;
            }
            if (progressCb && (y % 64 === 0 || y === h - 1)) {
                progressCb(Math.round((y + 1) * 100 / h));
            }
        }

        return new Blob([buffer], { type: 'image/tiff' });
    }

    function pngChunk(type, bytes) {
        const chunk = new Uint8Array(bytes.length + 12);
        const view = new DataView(chunk.buffer);
        view.setUint32(0, bytes.length);
        chunk.set(new TextEncoder().encode(type), 4);
        chunk.set(bytes, 8);
        let crc = 0xffffffff;
        for (let i = 4; i < chunk.length - 4; i++) {
            crc ^= chunk[i];
            for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
        }
        view.setUint32(chunk.length - 4, (crc ^ 0xffffffff) >>> 0);
        return chunk;
    }

    // Canvas.toBlob only encodes 8-bit channels. Encode genuine grayscale
    // 16-bit PNG samples in network byte order, with portable stored DEFLATE.
    function savePng16(s, progressCb) {
        const stride = 1 + s.width * 2;
        const raw = new Uint8Array(stride * s.height);
        const samples = new DataView(raw.buffer);
        const aa = s.smooth ? 2 : 1;
        for (let y = 0; y < s.height; y++) {
            for (let x = 0; x < s.width; x++) {
                samples.setUint16(y * stride + 1 + x * 2,
                    Math.round(getPixelHeight(x, y, s.width, s.height, s, aa) * 65535));
            }
            if (progressCb && y % 64 === 0) progressCb(Math.round((y + 1) * 100 / s.height));
        }
        const blocks = Math.ceil(raw.length / 65535);
        const zlib = new Uint8Array(2 + blocks * 5 + raw.length + 4);
        zlib.set([0x78, 0x01]);
        let offset = 2, a = 1, b = 0;
        for (let start = 0; start < raw.length; start += 65535) {
            const size = Math.min(65535, raw.length - start);
            zlib[offset++] = start + size === raw.length ? 1 : 0;
            zlib[offset++] = size & 255;
            zlib[offset++] = size >>> 8;
            zlib[offset++] = (~size) & 255;
            zlib[offset++] = ((~size) >>> 8) & 255;
            zlib.set(raw.subarray(start, start + size), offset);
            offset += size;
            for (let i = start; i < start + size; i++) {
                a = (a + raw[i]) % 65521;
                b = (b + a) % 65521;
            }
        }
        new DataView(zlib.buffer).setUint32(offset, ((b << 16) | a) >>> 0);
        const header = new Uint8Array(13);
        const view = new DataView(header.buffer);
        view.setUint32(0, s.width);
        view.setUint32(4, s.height);
        header[8] = 16;
        return new Blob([new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10]),
            pngChunk('IHDR', header), pngChunk('IDAT', zlib), pngChunk('IEND', new Uint8Array())],
            { type: 'image/png' });
    }

    function savePng(s, progressCb) {
        if (s.bits === 16) return savePng16(s, progressCb);
        const canvas = document.createElement('canvas');
        canvas.width = s.width;
        canvas.height = s.height;
        const ctx = canvas.getContext('2d');
        const imgData = ctx.createImageData(s.width, s.height);
        const data = imgData.data;
        const aa = s.smooth ? 2 : 1;

        for (let y = 0; y < s.height; y++) {
            for (let x = 0; x < s.width; x++) {
                const val = getPixelHeight(x, y, s.width, s.height, s, aa);
                const c = Math.round(val * 255);
                const p = (y * s.width + x) * 4;
                data[p] = c;
                data[p + 1] = c;
                data[p + 2] = c;
                data[p + 3] = 255;
            }
            if (progressCb && (y % 64 === 0 || y === s.height - 1)) {
                progressCb(Math.round((y + 1) * 100 / s.height));
            }
        }

        ctx.putImageData(imgData, 0, 0);

        return new Promise((resolve) => {
            canvas.toBlob((blob) => resolve(blob), 'image/png');
        });
    }

    async function triggerExport() {
        const s = getSettingsFromUI();
        const isEn = (document.documentElement.getAttribute('lang') === 'en') || (localStorage.getItem('lang') === 'en');

        if (s.minimum >= s.maximum) {
            alert(isEn ? 'White level must be higher than black level.' : 'Белый уровень должен быть выше чёрного.');
            return;
        }

        const statusLabel = document.getElementById('exportStatus');
        const downloadBtn = document.getElementById('downloadBtn');

        if (downloadBtn) downloadBtn.disabled = true;
        if (statusLabel) statusLabel.textContent = isEn ? 'Generating and saving…' : 'Генерация и сохранение…';

        try {
            // Let the disabled button and progress message paint before computation.
            await new Promise(resolve => setTimeout(resolve, 0));
            let blob;
            let filename;

            if (s.bits === 32) {
                filename = `scales_${s.width}x${s.height}_32bit_float.tif`;
                blob = saveTiff32Float(s, (p) => {
                    if (statusLabel) statusLabel.textContent = isEn ? `Saving TIFF: ${p}%` : `Сохранение TIFF: ${p}%`;
                });
            } else {
                filename = `scales_${s.width}x${s.height}_${s.bits}bit.png`;
                blob = await savePng(s, (p) => {
                    if (statusLabel) statusLabel.textContent = isEn ? `Saving PNG: ${p}%` : `Сохранение PNG: ${p}%`;
                });
            }

            if (!blob) throw new Error(isEn ? 'Image encoding failed' : 'Не удалось закодировать изображение');
            const url = URL.createObjectURL ? URL.createObjectURL(blob) : window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            setTimeout(() => URL.revokeObjectURL(url), 2000);

            if (statusLabel) statusLabel.textContent = isEn ? `Saved: ${filename}` : `Сохранено: ${filename}`;
        } catch (err) {
            console.error(err);
            if (statusLabel) statusLabel.textContent = isEn ? 'Export error' : 'Ошибка экспорта';
            alert((isEn ? 'Failed to generate file: ' : 'Не удалось сгенерировать файл: ') + err.message);
        } finally {
            if (downloadBtn) downloadBtn.disabled = false;
        }
    }

    // --- 6. Initialize App on DOM Load & Resize ---
    function initApp() {
        const curveCanvas = document.getElementById('curveCanvas');
        if (curveCanvas) {
            curveEditor = new SplineCurveEditor(curveCanvas, scheduleRender);
        }

        const ids = ['shape', 'direction', 'width', 'height', 'columns', 'rows',
            'overlap', 'stagger', 'gamma', 'minimum', 'maximum', 'invert', 'depth', 'tiles', 'smooth'];

        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('input', scheduleRender);
                el.addEventListener('change', scheduleRender);
            }
        });

        const resetBtn = document.getElementById('resetTemplateBtn');
        if (resetBtn) resetBtn.addEventListener('click', resetTemplateDefaults);

        const downloadBtn = document.getElementById('downloadBtn');
        if (downloadBtn) downloadBtn.addEventListener('click', triggerExport);

        const btnResetCurve = document.getElementById('btnResetCurve');
        if (btnResetCurve) btnResetCurve.addEventListener('click', () => curveEditor && curveEditor.resetLinear());

        const btnSCurve = document.getElementById('btnSCurve');
        if (btnSCurve) btnSCurve.addEventListener('click', () => curveEditor && curveEditor.setSCurve());

        const btnConcave = document.getElementById('btnConcave');
        if (btnConcave) btnConcave.addEventListener('click', () => curveEditor && curveEditor.setConcave());

        const btnConvex = document.getElementById('btnConvex');
        if (btnConvex) btnConvex.addEventListener('click', () => curveEditor && curveEditor.setConvex());

        window.addEventListener('resize', scheduleRender);

        renderPreview();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initApp);
    } else {
        initApp();
    }

})();
