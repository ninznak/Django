/**
 * Draw blurred dark links between background orbs when centers are closer than r1 + r2.
 */
(function () {
  "use strict";

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return;
  }

  var SVG_NS = "http://www.w3.org/2000/svg";
  var orbs = Array.prototype.slice.call(document.querySelectorAll(".orb"));
  var svg = document.getElementById("orb-links-layer");
  if (!svg || orbs.length < 2) {
    return;
  }

  var lines = Object.create(null);
  var proximityScale = 1.12;

  function pairKey(i, j) {
    return i < j ? i + "-" + j : j + "-" + i;
  }

  function orbMetrics(el) {
    var r = el.getBoundingClientRect();
    var size = Math.max(r.width, r.height);
    return {
      x: r.left + r.width * 0.5,
      y: r.top + r.height * 0.5,
      radius: size * 0.5,
    };
  }

  function tick() {
    var metrics = orbs.map(orbMetrics);
    var active = Object.create(null);

    for (var i = 0; i < metrics.length; i += 1) {
      for (var j = i + 1; j < metrics.length; j += 1) {
        var a = metrics[i];
        var b = metrics[j];
        var dx = a.x - b.x;
        var dy = a.y - b.y;
        var dist = Math.sqrt(dx * dx + dy * dy);
        var threshold = (a.radius + b.radius) * proximityScale;
        var key = pairKey(i, j);

        if (dist < threshold) {
          var t = 1 - dist / threshold;
          var strength = t * t;
          var line = lines[key];
          if (!line) {
            line = document.createElementNS(SVG_NS, "line");
            line.setAttribute("class", "orb-link");
            svg.appendChild(line);
            lines[key] = line;
          }
          line.setAttribute("x1", String(a.x));
          line.setAttribute("y1", String(a.y));
          line.setAttribute("x2", String(b.x));
          line.setAttribute("y2", String(b.y));
          line.setAttribute(
            "stroke-width",
            String(6 + strength * 32)
          );
          line.style.opacity = String(0.06 + strength * 0.48);
          active[key] = true;
        }
      }
    }

    Object.keys(lines).forEach(function (key) {
      if (!active[key]) {
        lines[key].remove();
        delete lines[key];
      }
    });

    requestAnimationFrame(tick);
  }

  requestAnimationFrame(tick);
})();
