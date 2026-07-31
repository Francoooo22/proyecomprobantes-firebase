# Proyecto: Web de Comprobantes Automatizada - Firebase + n8n

## Resumen Ejecutivo

Sistema para automatizar la gestión administrativa de un grupo de empresas de servicios turísticos con múltiples CUITs (Grupo Lantier, Aramendi, Wolf, Family Group). El proyecto se enfoca en la automatización de comprobantes bancarios y conciliación.

## Contexto del Negocio

### Empresa
- **Tipo**: Empresa de servicios turísticos (grupo con varios CUITs)
- **Sub-rubros**: 
  - Venta de viajes por mayor
  - Venta por menor
  - Viajes de egresados
  - Venta de transportes por km
- **Sistemas actuales**: REDEVT, PAXMANAGER, Excel
- **Sucursales**: Múltiples
- **Vendedores**: Múltiples por sucursal

### Problema Actual
1. **Comprobantes**: Llegan por WhatsApp (PDFs e imágenes de comprobantes físicos)
2. **Volumen**: ~55 comprobantes/día
3. **Proceso manual**: Pegar en Excel, cruzar contra REDEVT, click por click
4. **Conciliación**: No se hacía (estaba desactualizada 3 meses)
5. **Multi-CUIT**: Los comprobantes pueden ser de cualquier CUIT del grupo

### Solución Propuesta
- **Web en Firebase** para subir comprobantes (reemplaza WhatsApp)
- **OCR con Google Vision** para extraer datos automáticamente
- **n8n** para automatizar conciliación y contabilidad

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    WEB (Firebase Hosting)                         │
├─────────────────────────────────────────────────────────────────┤
│  HTML/CSS/JavaScript vanilla                                     │
│  Auth: Email/Contraseña (vendedores + supervisores)              │
│  Formulario: Sucursal + Comprobante (imagen)                     │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FIREBASE                                       │
├─────────────────────────────────────────────────────────────────┤
│  Auth: Usuarios (vendedores/supervisores)                        │
│  Storage: Imágenes de comprobantes                               │
│  Firestore: Datos extraídos + metadatos                          │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    n8n (Automatización)                           │
├─────────────────────────────────────────────────────────────────┤
│  Trigger: Nuevo comprobante en Firestore                         │
│  OCR: Google Vision (imágenes inclinadas)                        │
│  Parser: Extraer datos por patrón (BNA, MODO, Mercado Pago)     │
│  Matching: Con banco (Sheet)                                     │
│  Registro: En REDEVT (si es posible)                             │
└─────────────────────────────────────────────────────────────────┘
```

## Fases de Implementación

### Fase 1: Configuración Firebase (1-2 horas)
1. Crear proyecto en Firebase Console
2. Habilitar servicios:
   - Authentication (Email/Password)
   - Firestore Database
   - Storage
   - Hosting
3. Obtener configuración Firebase SDK
4. Configurar reglas de Firestore
5. Configurar reglas de Storage

### Fase 2: Desarrollo Frontend (4-6 horas)

#### Estructura del Proyecto
```
📁 comprobantes-web/
├── 📁 public/
│   ├── 📄 index.html
│   ├── 📁 css/
│   │   └── 📄 styles.css
│   ├── 📁 js/
│   │   ├── 📄 auth.js
│   │   ├── 📄 upload.js
│   │   └── 📄 app.js
│   └── 📁 assets/
├── 📄 firebase.json
├── 📄 .firebaserc
└── 📄 firestore.rules
```

#### Funcionalidades
| Módulo | Descripción |
|--------|-------------|
| **Login** | Email/contraseña, redirige según rol |
| **Subir comprobante** | Seleccionar sucursal + subir imagen |
| **OCR automático** | Google Vision extrae texto |
| **Parser por patrón** | Detecta BNA, MODO, Mercado Pago y extrae campos |
| **Historial** | Lista de comprobantes del vendedor |
| **Aprobación** | Supervisor aprueba/rechaza |

### Fase 3: Integración OCR (2-3 horas)

#### Cloud Function en Firebase
- Trigger: Cuando se sube comprobante a Storage
- Llamar a Google Vision API
- Extraer texto
- Guardar en Firestore

#### Parsers por Patrón
| Comprobante | Campos a extraer |
|-------------|------------------|
| **BNA** | Nombre, monto, fecha, CBU destino |
| **MODO** | Nombre, monto, fecha, alias/CBU |
| **Mercado Pago** | Nombre, monto, fecha, destino |

### Fase 4: Integración n8n (3-4 horas)

#### Configuración
- Trigger Firestore (nuevo comprobante)
- Google Vision OCR (backup)
- Matching con banco (Sheet)
- Reportes automáticos

### Fase 5: Testing y Deploy (2-3 horas)

#### Tareas
1. Probar login
2. Probar subida comprobante
3. Probar OCR
4. Probar matching
5. Deploy a Firebase Hosting
6. Capacitar usuarios

## Firestore Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /comprobantes/{doc} {
      allow read: if request.auth.uid == resource.data.vendedor_uid 
                  || get(/databases/$(database)/documents/usuarios/$(request.auth.uid)).data.rol == 'supervisor';
      allow create: if request.auth != null;
      allow update: if get(/databases/$(database)/documents/usuarios/$(request.auth.uid)).data.rol == 'supervisor';
    }
  }
}
```

## Costos Estimados

| Servicio | Costo |
|----------|-------|
| Firebase Hosting | Gratis |
| Firebase Auth | Gratis |
| Firebase Storage | Gratis |
| Firestore | Gratis |
| Google Vision OCR | ~$1 USD/mes |
| **Total** | **~$1 USD/mes** |

## Dependencias

### Frontend
- Firebase SDK (auth, firestore, storage)
- JavaScript vanilla (sin frameworks)

### Backend
- Firebase Cloud Functions
- Google Vision API
- n8n (self-hosted o cloud)

### Integraciones
- Google Sheets (datos del banco)
- REDEVT (sistema actual)
- n8n (automatización)

## Cronograma Estimado

| Fase | Tiempo |
|------|--------|
| Configuración Firebase | 1-2 horas |
| Desarrollo Frontend | 4-6 horas |
| Integración OCR | 2-3 horas |
| Integración n8n | 3-4 horas |
| Testing y Deploy | 2-3 horas |
| **Total** | **12-18 horas** |

## Próximos Pasos

1. **Aprobación del plan**: Confirmar que la arquitectura es correcta
2. **Configuración Firebase**: Crear proyecto y servicios
3. **Desarrollo frontend**: Crear web de subida de comprobantes
4. **Integración OCR**: Configurar Google Vision y parsers
5. **Integración n8n**: Conectar con banco y REDEVT
6. **Testing**: Probar con vendedores reales
7. **Deploy**: Publicar en Firebase Hosting
8. **Capacitación**: Enseñar a vendedores y supervisores

## Notas Técnicas

### OCR - Google Vision
- **Costo**: Gratis hasta 1000 unidades/mes (~$1 USD después)
- **Capacidades**: 
  - PDFs ✅
  - Imágenes (JPG, PNG) ✅
  - Imágenes inclinadas (hasta 45°) ✅
  - Múltiples idiomas ✅
- **Alternativas**: 
  - pdf-parse (gratis, solo PDFs text-based)
  - Azure OCR (gratis hasta 5000)
  - Tesseract (open source, menos preciso)

### Autenticación
- Email/contraseña para vendedores y supervisores
- Roles: vendedor (ve propios), supervisor (ve todos)
- Firestore rules para seguridad

### Matching con Banco
- **Prioridad 1**: Monto exacto (tolerancia ±0.3% por impuestos)
- **Prioridad 2**: Últimos 4 dígitos comprobante + monto cercano
- **Prioridad 3**: Fecha + CUIT + monto dentro de rango
- **Prioridad 4**: Matching many-to-one (1 banco → N comprobantes)
- **Alerta**: Revisión manual para no conciliados

### Diferencias Comunes
- Impuestos: SIRCREB, SIRTAC (0.3%)
- Agrupación: Un pago puede agrupar varias transacciones
- Fechas: Diferencia entre fecha operación y acreditación

## Seguridad

### Firestore Rules
- Vendedores solo ven sus comprobantes
- Supervisores ven todos
- Solo usuarios autenticados pueden crear
- Solo supervisores pueden actualizar estado

### Storage Rules
- Solo imágenes de comprobantes
- Tamaño máximo: 10MB
- Tipos permitidos: JPG, PNG, PDF

## Métricas de Éxito

1. **Tiempo de procesamiento**: Reducir de 1 semana a minutos
2. **Precisión OCR**: >95% de extracción correcta
3. **Tasa de conciliación automática**: >80%
4. **Satisfacción del usuario**: vendedores y supervisores satisfechos
5. **Reducción de errores**: Eliminar errores manuales

## Riesgos y Mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| OCR falla con imágenes borrosas | Validación de calidad antes de procesar |
| Cambios en formato de comprobantes | Parsers flexibles y actualizables |
| Integración con REDEVT compleja | API o exportación CSV como alternativa |
| Resistencia al cambio de vendedores | Capacitación y soporte continuo |

---

**Última actualización**: $(date)
**Estado**: Plan aprobado, pendiente de implementación
**Responsable**: Franco
**Presupuesto**: ~$1 USD/mes (Google Vision OCR)