declare module "plotly.js/dist/plotly.min.js" {
  const Plotly: {
    react(element: HTMLElement, data: object[], layout: object, config: object): Promise<unknown>;
    purge(element: HTMLElement): void;
  };
  export default Plotly;
}
