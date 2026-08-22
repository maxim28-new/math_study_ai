"use strict";

(function (root) {
  const TERMS = [
    {
      id: "compass",
      words: ["圆规"],
      kid: "画圆的工具。一只脚扎在中间，另一只脚转一圈，就能画出圆。",
      example: "把圆规两脚张开，跟线段 AB 一样宽，再转一圈。",
      highlight: "compass",
    },
    {
      id: "center",
      words: ["圆心"],
      kid: "圆最中间的那个点。圆边上的每一点，到它都一样远。",
      example: "这个圆的圆心是点 A。",
      highlight: "center",
    },
    {
      id: "radius",
      words: ["半径"],
      kid: "从圆心连到圆边的这一段。这段有多长，圆就有多大。",
      example: "圆规两脚之间的宽度，就是这个圆的半径。",
      highlight: "radius",
    },
    {
      id: "intersection",
      words: ["交点"],
      kid: "两条线段、两条直线或两个圆碰到一起的地方。",
      example: "两个圆交叉时，上面那个碰到的点可以记作 P。",
      highlight: "intersection",
    },
    {
      id: "segment",
      words: ["线段", "直线段"],
      kid: "两个点之间连起来的这一段。两头都有点，到此为止，不能再往外画。",
      example: "A 和 B 连起来的那一条，就是线段 AB。课本里说的直线段，也是这个意思。",
      highlight: "segment",
    },
    {
      id: "line",
      words: ["直线"],
      kid: "也能穿过两个点，可是两头都能一直延长，没有头也没有尾。",
      example: "把线段 AB 两头再往外画，想的时候就是一条直线。折痕、尺边都要当成直线。",
      highlight: "line",
    },
    {
      id: "equilateral",
      words: ["正三角形"],
      kid: "三条边一样长的三角形。",
      example: "如果 PA、PB、AB 一样长，三角形 PAB 就是正三角形。",
      highlight: "equilateral",
    },
    {
      id: "square",
      words: ["正方形"],
      kid: "四条边一样长、四个角都是直角的方形。",
      example: "每边 2 块积木，就能围成一个小正方形。",
      highlight: "square",
    },
    {
      id: "pattern",
      words: ["规律"],
      kid: "一直重复出现的小秘密。看懂它，就能猜后面是什么。",
      example: "红、红、蓝，红、红、蓝，就是一种规律。",
      highlight: "pattern",
    },
    {
      id: "arrange",
      words: ["排列"],
      kid: "把东西按不同顺序排队。顺序变了，就算另一种排法。",
      example: "红花、蓝花和黄花，谁排第一可以不一样。",
      highlight: "",
    },
    {
      id: "combine",
      words: ["组合"],
      kid: "只看选了谁，先不管谁先谁后。",
      example: "选红花和蓝花，不管先说谁，都是同一种选法。",
      highlight: "",
    },
    {
      id: "equation",
      words: ["等式"],
      kid: "等号两边一样多，像一架两边一样重的天平。",
      example: "7 减 2 和 5 一样多，就可以写成等式。",
      highlight: "",
    },
    {
      id: "fraction",
      words: ["分数"],
      kid: "把一样的东西平均切开，再拿走其中几份。",
      example: "一块饼切成 4 份，拿走 1 份，就是四分之一。",
      highlight: "",
    },
  ];

  const byId = {};
  const wordIndex = [];
  TERMS.forEach((term) => {
    byId[term.id] = term;
    term.words.forEach((word) => wordIndex.push({ word, id: term.id }));
  });
  wordIndex.sort((a, b) => b.word.length - a.word.length);

  root.XiaoouTerms = {
    all: TERMS,
    byId,
    wordIndex,
  };
})(typeof globalThis !== "undefined" ? globalThis : this);
