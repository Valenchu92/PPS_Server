# Diseño Responsivo y Adaptabilidad (Móvil & PC)

El panel "SatStreamPRO" de la **Galería de Imágenes** está diseñado bajo los principios de *Responsive Web Design* (Diseño Web Adaptable). Esto garantiza que un único servidor Nginx entregue el mismo código fuente a cualquier dispositivo y sea el navegador cliente el responsable de orquestar y reformatear la presentación del portal.

A continuación se documentan las técnicas implementadas para asegurar la fluidez entre monitores panorámicos y pantallas limitadas de smartphones:

## 1. Declaración de Viewport
Para evitar que los dispositivos móviles intenten emular resoluciones amplias "alejando" el plano (zoom out nativo), se forzó la relación de escala base mediante la inclusión de la etiqueta viewport en el `<head>` de `index.html`:

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```

## 2. Reflujo Dinámico con Media Queries (`style.css`)
El CSS principal fue segmentado con puntos de quiebre (breakpoints) estratégicos utilizando la regla `@media`:

### Transición a un solo plano (Tablets y móviles cruzados)
Cuando la pantalla presenta **menos de 992px** de espacio horizontal, se anula la disposición inicial de doble columna (`2fr 1fr`).
```css
@media (max-width: 992px) {
    .content-wrapper {
        grid-template-columns: 1fr;
    }
}
```
*Efecto:* Los paneles laterales (como el Nowcast a corto plazo) se desacoplan de la derecha y fluyen orgánicamente bajo el modelo principal para prevenir colisiones textuales.

### Especialización para Smartphones (`max-width: 600px`)
Por debajo de los 600 píxeles, la interfaz entra en "Mobile Mode":
- **Cabeceras Inteligentes:** El logo y los relojes (UTC/Local) que operaban con separación dual (Flex *space-between*) pierden prioridad de fila y colapsan en una columna para aprovechar el espacio.
- **Grillas Simplificadas:** Las métricas de Clima Actual asumen una estructura compacta y balanceada de 2x2.
- **Micro-interacciones Táctiles:** Las pestañas meteorológicas (`provider-tabs` y `predictive-tabs`) habilitan comportamiento `overflow-x: auto`, sustituyendo el empaquetado clásico por una barra deslizadora táctil con el pulgar.

## 3. Prevención del "Grid Blow-out"
Un desafío abordado fue la tendencia de la interfaz a romper el margen del dispositivo (expansión a más del `100vw`), exigiendo scroll lateral global debido a componentes como las predicciones temporales extendidas del SMN o OWM que no deseaban encogerse.

Se solucionó implementando límites físicos estrictos en los contenedores padres:
```css
/* Limita las columnas forzando a Flex y Grid a respetar el ancho total */
.content-wrapper > div, .content-wrapper > aside {
    min-width: 0;
}
```
Esto anula el comportamiento natural de *CSS Grid* donde determina el ancho `auto` en relación con el elemento hijo más grande. Seguidamente, se liberalizó a la librería *Chart.js* de sus forzantes de origen y se impuso `width: 100%`: 

```css
@media (max-width: 600px) {
    .pred-canvas-wrapper {
        min-width: unset !important;
        width: 100%;
    }
}
```
Con ello, el módulo predictivo acata las limitaciones del celular, logrando que sea visible al primer golpe de vista, y el scroll lateral queda acotado y relegado **exclusivamente a los cuadros selectores**.
