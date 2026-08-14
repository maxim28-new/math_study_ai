"use strict";
(function (root) {
  const A = root.XiaoouActivity || {};
  A.mountSnapGrid = A.mountSnapGrid || function () {
    return { freeze() {}, destroy() {}, getSnapshot() { return null; }, getOccupancy() { return { occupied: [], trayLeft: 0 }; } };
  };
  root.XiaoouActivity = A;
})(typeof globalThis !== "undefined" ? globalThis : this);
