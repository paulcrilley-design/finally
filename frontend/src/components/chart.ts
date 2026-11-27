/** Axis and tooltip styling shared by the charts (OUI_FORMAT.md section 2). */
export const AXIS = {
  stroke: "var(--stroke)",
  tick: { fill: "var(--gray-text)", fontSize: 12 },
  tickLine: false,
};

export const TOOLTIP = {
  contentStyle: { borderRadius: 12, borderColor: "var(--stroke)", fontSize: 12 },
  isAnimationActive: false,
};
