/**
 * Bloquea el scroll del body (para overlays: Drawer, Modal) SIN provocar el
 * salto de layout que ocurre al desaparecer la barra de scroll.
 *
 * Al poner `overflow: hidden` el navegador quita la scrollbar y el contenido se
 * ensancha ~15px → al abrir/cerrar el overlay la página "salta". Compensamos
 * reservando ese ancho como `padding-right` mientras dura el bloqueo.
 *
 * Devuelve la función de unlock (restaura los estilos previos). Pensado para
 * usarse como cleanup de un useLayoutEffect: `return lockBodyScroll();`.
 */
export function lockBodyScroll(): () => void {
  const scrollbarWidth =
    window.innerWidth - document.documentElement.clientWidth;
  const prevOverflow = document.body.style.overflow;
  const prevPaddingRight = document.body.style.paddingRight;

  document.body.style.overflow = "hidden";
  if (scrollbarWidth > 0) {
    document.body.style.paddingRight = `${scrollbarWidth}px`;
  }

  return () => {
    document.body.style.overflow = prevOverflow;
    document.body.style.paddingRight = prevPaddingRight;
  };
}
