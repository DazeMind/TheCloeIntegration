from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone


def _d(valor):
    return Decimal(str(valor))


def clp_entero(valor):
    """Redondea un monto a CLP entero (half-up), p. ej. 8319.32 -> 8319."""
    return int(_d(valor).to_integral_value(rounding=ROUND_HALF_UP))


def monto_linea_clp(detalle):
    """Monto bruto por línea = cantidad * precio_unitario - descuento, entero CLP."""
    return clp_entero(detalle.cantidad * detalle.precio_unitario - detalle.descuento)


def _qty_str(cantidad):
    """Cantidad como str sin ceros trailing: 2.0000 -> '2', 1.5000 -> '1.5'."""
    valor = _d(cantidad)
    return format(valor.normalize(), 'f')


def _es_factura(venta):
    return venta.document_type == 'INVOICE'


def build_dte_payload(venta, empresa):
    """
    Construye el payload JSON de SimpleFactura para un DTE.

    Boleta  -> TipoDTE 39 (venta presencial, IndServicioBoleta=3).
    Factura -> TipoDTE 33 (FmaPago 1 contado / 2 crédito, MntBruto=1).

    Manejo de IVA (crítico, verificado contra la API):
    - Boleta: los precios/items de la venta vienen BRUTOS (IVA incl.) de DeCloé.
      SimpleFactura asume brutos por defecto en boletas, así que MntNeto/IVA se
      calculan aquí (MntNeto = gravado / 1.19) y se envían explícitos.
    - Factura: por defecto SimpleFactura asume NETOS, por eso se manda
      IdDoc.MntBruto=1 para que interprete los MontoItem como brutos y el
      MntNeto calculado sea coherente con la base imponible del SII.
    - Todos los montos viajan como STRING (formato del ejemplo oficial).

    Los montos se dividen entre gravado (impuesto=IVA) y exento (EXEMPT).
    """
    es_factura = _es_factura(venta)
    tipo = 33 if es_factura else 39
    fecha = timezone.localtime(venta.issued_at).date().isoformat()

    gravado = Decimal('0')
    exento = Decimal('0')
    detalles = []
    for detalle in venta.detalles.all().order_by('linea'):
        monto_item = monto_linea_clp(detalle)
        if detalle.impuesto == 'EXEMPT':
            exento += monto_item
        else:
            gravado += monto_item

        item = {
            'NroLinDet': str(detalle.linea),
            'NmbItem': detalle.nombre_producto,
        }
        if detalle.codigo_producto:
            item['CdgItem'] = [{'TpoCodigo': 'INT1', 'VlrCodigo': detalle.codigo_producto}]
        if detalle.descuento:
            item['DescuentoMonto'] = str(clp_entero(detalle.descuento))
        item['QtyItem'] = _qty_str(detalle.cantidad)
        item['UnmdItem'] = 'un'
        item['PrcItem'] = str(clp_entero(detalle.precio_unitario))
        item['MontoItem'] = str(monto_item)
        detalles.append(item)

    # Totales CLP (enteros).
    neto = clp_entero(gravado / Decimal('1.19')) if gravado else 0
    iva = int(gravado) - neto if gravado else 0
    mnt_exe = int(exento)
    mnt_total = int(gravado + exento)

    id_doc = {
        'TipoDTE': tipo,
        'FchEmis': fecha,
        'FchVenc': fecha,
    }
    if es_factura:
        id_doc['FmaPago'] = 1 if venta.payment_method == 'CASH' else 2
        id_doc['MntBruto'] = 1
    else:
        id_doc['IndServicioBoleta'] = 3

    # Emisor. Gotcha real: la factura usa 'RznSoc'/'GiroEmis' (no RznSocEmisor).
    emisor = {
        'RUTEmisor': empresa.rut_emisor,
        'DirOrigen': empresa.direccion or '',
        'CmnaOrigen': empresa.comuna or '',
    }
    if es_factura:
        emisor['RznSoc'] = empresa.razon_social
        emisor['GiroEmis'] = empresa.giro or ''
        emisor['Acteco'] = [620200]
        emisor['CorreoEmisor'] = empresa.email or ''
        if empresa.telefono:
            emisor['Telefono'] = [empresa.telefono]
        if empresa.ciudad:
            emisor['CiudadOrigen'] = empresa.ciudad
    else:
        emisor['RznSocEmisor'] = empresa.razon_social
        emisor['GiroEmisor'] = empresa.giro or ''

    # Receptor.
    receptor = {
        'RUTRecep': _rut_receptor(venta),
        'RznSocRecep': (venta.cliente_nombre or '').strip() or 'Consumidor Final',
    }
    if venta.cliente_direccion:
        receptor['DirRecep'] = venta.cliente_direccion
    if venta.cliente_comuna:
        receptor['CmnaRecep'] = venta.cliente_comuna
    if venta.cliente_ciudad:
        receptor['CiudadRecep'] = venta.cliente_ciudad

    # Totales.
    totales = {
        'MntNeto': str(neto),
        'IVA': str(iva),
        'MntTotal': str(mnt_total),
    }
    if es_factura:
        totales['TasaIVA'] = '19'
    if mnt_exe:
        totales['MntExe'] = str(mnt_exe)

    return {
        'Documento': {
            'Encabezado': {
                'IdDoc': id_doc,
                'Emisor': emisor,
                'Receptor': receptor,
                'Totales': totales,
            },
            'Detalle': detalles,
        }
    }


def _rut_receptor(venta):
    rut = (venta.cliente_rut or '').strip()
    # Boleta sin receptor: RUT genérico de consumidor final.
    return rut or '66666666-6'