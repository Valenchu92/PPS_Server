# Arquitectura del Sistema NOAA

El sistema está diseñado en una serie de bloques que abarcan desde la recepción de la señal de radio hasta su procesamiento y posterior visualización. A continuación se presenta el diagrama general de la infraestructura:

```mermaid
graph TD
    %% Bloque 1: Adquisición
    subgraph Adquisición ["1. Adquisición y Demodulación"]
        A["Antena V-Dipole / QFH"] --> B["SDR RTL-SDR"]
        B --> C["Software SDR SDR# / GQRX / SatDump"]
        C --"Demodulación FM"--> D["Archivo de Audio .WAV"]
    end

    %% Bloque 2: Procesamiento
    subgraph Procesamiento ["2. Procesamiento e Ingesta"]
        D --"Volumen: input-wav/"--> E{{"Contenedor: Processor"}}
        E --"Decodificación APT (noaa-apt)"--> F["Imágenes Satelitales .PNG<br>+ Metadatos y Telemetría"]
    end

    %% Bloque 3: Almacenamiento
    subgraph Almacenamiento ["3. Almacenamiento y Notificación"]
        F --"Volumen: png-images/"--> G[("Sistema de Archivos Local")]
        E --"API Call (Tiempo Real)"--> H["Contenedor: Immich Server"]
    end

    %% Bloque 4: Visualización
    subgraph Visualizacion ["4. Visualización y Uso"]
        G -.-> H
        H -.-> I["Bases de Datos<br>Postgres + Redis"]
        H --"Búsquedas, Álbumnes y Reconocimiento"--> J["Usuario General / Público<br>Galería Web/Móvil Immich"]
        
        G --"Análisis de Telemetría (Falso Color/Mapas)"--> K["Meteorólogos / Especialistas<br>Sistemas SIG (QGIS) / SatDump"]
    end

    %% Estilos Adicionales
    classDef hardware fill:#e0f2fe,stroke:#0369a1,stroke-width:2px,color:#0c4a6e;
    classDef soft fill:#fecdd3,stroke:#be123c,stroke-width:2px,color:#881337;
    classDef docker fill:#dcfce7,stroke:#15803d,stroke-width:2px,color:#14532d;
    classDef users fill:#fef08a,stroke:#a16207,stroke-width:2px,color:#713f12;

    class A,B hardware;
    class C soft;
    class E,H docker;
    class J,K users;
```

## Componentes del Entorno Docker

El sistema se compone de los siguientes contenedores principales que interactúan entre sí:

* **Processor (noaa-apt):** Es el corazón del procesamiento. Detecta instantáneamente nuevos archivos de audio, los convierte a imágenes y notifica a la galería.
* **Immich:** Provee una interfaz tipo "Google Photos" para el público general.
* **Bases de Datos:** PostgreSQL y Redis almacenan los metadatos fotográficos y optimizan las consultas.
* **n8n:** Orquestador reservado para automatizaciones futuras (ej. descargas en la nube).
