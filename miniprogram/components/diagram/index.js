const { measure, drawToCanvas } = require("../../utils/diagram.js");

Component({
  properties: {
    spec: { type: Object, value: null },
    caption: { type: String, value: "" },
  },
  data: { cssW: 280, cssH: 120 },
  observers: {
    spec(s) {
      if (s && s.type) {
        const m = measure(s);
        this.setData({ cssW: m.w, cssH: m.h }, () => this.draw());
      }
    },
  },
  lifetimes: {
    ready() {
      if (this.properties.spec) this.draw();
    },
  },
  methods: {
    draw() {
      const spec = this.properties.spec;
      if (!spec) return;
      const query = this.createSelectorQuery();
      query.select("#cv").fields({ node: true, size: true }).exec((res) => {
        if (!res || !res[0] || !res[0].node) return;
        const canvas = res[0].node;
        const ctx = canvas.getContext("2d");
        const dpr = wx.getWindowInfo ? wx.getWindowInfo().pixelRatio : 2;
        const w = this.data.cssW;
        const h = this.data.cssH;
        canvas.width = w * dpr;
        canvas.height = h * dpr;
        ctx.scale(dpr, dpr);
        drawToCanvas(ctx, spec, w, h);
      });
    },
  },
});
