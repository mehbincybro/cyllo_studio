# -*- coding: utf-8 -*-
import requests
import xml.etree.ElementTree as ET
from datetime import date, datetime
from odoo import _, fields, models
from odoo import release

from odoo.exceptions import UserError


class DeliveryCarrier(models.Model):
    """
        This class inherits 'delivery.carrier' model for using delivery carrier
        functionality
    """
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(selection_add=[('dhl', 'DHL')],
                                     ondelete={'dhl': 'set default'})
    service_type = fields.Selection(selection=[
        ('0', '0 - LOGISTIC SERVICES'),
        ('1', '1 - DOMESTIC EXPRESS 12.00 '),
        ('2', '2 - B2C'),
        ('3', '3 - B2C'),
        ('4', '4 - JET LINE'),
        ('5', '5 - SPRINT LINE'),
        ('6', '6 - SECURE LINE'),
        ('7', '7 - EXPRESS EASY'),
        ('8', '8 - EXPRESS EASY'),
        ('9', '9 - EURO PACK'),
        ('A', 'A - AUTO REVERSALS'),
        ('B', 'B - BREAK BULK EXPRESS'),
        ('C', 'C - MEDICAL EXPRESS'),
        ('D', 'D - EXPRESS WORLDWIDE'),
        ('E', 'E - EXPRESS 9.00'),
        ('F', 'F - FREIGHT WORLDWIDE'),
        ('G', 'G - DOMESTIC ECONOMY SELECT'),
        ('H', 'H - ECONOMY SELECT'),
        ('I', 'I - BREAK BULK ECONOMY SELECT'),
        ('J', 'J - JUMBO BOX'),
        ('K', 'K - EXPRESS 9.00'),
        ('L', 'L- EXPRESS 10:30'),
        ('M', 'M - EXPRESS 10:30'),
        ('N', 'N - DOMESTIC EXPRESS'),
        ('O', 'O - DOM EXPRESS 10:30'),
        ('P', 'P - EXPRESS WORLDWIDE'),
        ('Q', 'Q - MEDICAL EXPRESS'),
        ('R', 'R - GLOBAL MAIL EXPRESS'),
        ('S', 'S - SAME DAY'),
        ('T', 'T - EXPRESS 12.00'),
        ('U', 'U - EXPRESS WORLDWIDE'),
        ('V', 'V - EURO PACK'),
        ('W', 'W - ECONOMY SELECT'),
        ('X', 'X - EXPRESS ENVELOP'),
        ('Y', 'Y - EXPRESS 12.00'),
        ('Z', 'Z - DESTINATION CHARGES')], help="Service Types in DHL")
    weight_uom = fields.Selection(selection=[('KG', 'KG'), ('P', 'P')],
                                  string="Unit of Measure", help="Package Unit of Measure")
    region = fields.Selection(selection=[('asiapacific', 'Asia Pacific'), ('america', 'America'),
                                         ('europe', 'Europe')], help="Region codes for Shipping")
    label_template = fields.Selection(selection=[('label', '8*4_A4_PDF'), ],
                                      help="Label Template for Shipping Label")
    label_format = fields.Selection(selection=[('PDF', 'PDF'), ('ZPL2', 'ZPL2'), ],
                                    help="Label Format for template")
    site_id = fields.Char(string="DHL Site ID", help="DHL Customer's site id")
    password = fields.Char(string="DHL Password", help="DHL Customer Password")
    account_no = fields.Integer(string="DHL Account Number",
                                help="Account number of DHL Customer")
    package_type_id = fields.Many2one("stock.package.type", string="Package Type",
                                      help="Package Types available in DHL")
    dimension_unit = fields.Selection(selection=[('I', 'I'), ('CM', 'CM')], string="Dimensional Unit",
                                      help="Dimensional Unit available in dhl")
    insured_value = fields.Float(help="Insurance value in DHL")
    dutiable = fields.Boolean(help="Check package is dutiable or not")

    def dhl_rate_shipment(self, order):
        """
            This function calculates the shipping rate for a given order
            using DHL's services.
        """
        if not self.account_no:
            return _("Account Number is Missing")
        if not self.site_id:
            return _("Site ID is Missing")
        if not self.password:
            return _("Password is Missing")
        weight = 0
        for rec in order.order_line:
            weight = weight + (rec.product_uom_qty * rec.product_id.weight)
        xml_request = f'<?xml version="1.0" encoding="utf-8"?>' \
                      f'<ns0:DCTRequest xmlns:ns0="http://www.dhl.com" schemaVersion="2.0">' \
                      f'<GetQuote>' \
                      f'    <Request>' \
                      f'        <ServiceHeader>' \
                      f'            <MessageTime>{datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")}</MessageTime>' \
                      f'            <MessageReference>ref:{datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")}' \
                      f'</MessageReference>' \
                      f'            <SiteID>{self.site_id}</SiteID>' \
                      f'            <Password>{self.password}</Password>' \
                      f'        </ServiceHeader>' \
                      f'        <MetaData>' \
                      f'            <SoftwareName>{release.product_name}</SoftwareName>' \
                      f'            <SoftwareVersion>{release.series}</SoftwareVersion>' \
                      f'        </MetaData>' \
                      f'    </Request>' \
                      f'    <From>' \
                      f'        <CountryCode>{self.env.company.country_code}</CountryCode>' \
                      f'        <Postalcode>{self.env.company.zip}</Postalcode>' \
                      f'        <City>{self.env.company.city}</City>' \
                      f'    </From>' \
                      f'    <BkgDetails>' \
                      f'        <PaymentCountryCode>{order.warehouse_id.partner_id.country_code}' \
                      f'</PaymentCountryCode>' \
                      f'        <Date>{date.today()}</Date>' \
                      f'        <ReadyTime>PT1H2M</ReadyTime>' \
                      f'        <DimensionUnit>{self.dimension_unit}</DimensionUnit>' \
                      f'        <WeightUnit>{self.weight_uom}</WeightUnit>' \
                      f'        <Pieces>' \
                      f'            <Piece>' \
                      f'                <PieceID>0</PieceID>' \
                      f'                <PackageTypeCode>{self.package_type_id.barcode}</PackageTypeCode>' \
                      f'                <Height>{self.package_type_id.height}</Height>' \
                      f'                <Depth>{self.package_type_id.packaging_length}</Depth>' \
                      f'                <Width>{self.package_type_id.width}</Width>' \
                      f'                <Weight>{weight}</Weight>' \
                      f'            </Piece>' \
                      f'        </Pieces>' \
                      f'        <PaymentAccountNumber>{self.account_no}</PaymentAccountNumber>' \
                      f'        <IsDutiable>{"N" if self.dutiable is False else "Y"}</IsDutiable>' \
                      f'        <NetworkTypeCode>AL</NetworkTypeCode>' \
                      f'        <InsuredValue>0</InsuredValue>' \
                      f'        <InsuredCurrency>{self.env.company.currency_id.name}</InsuredCurrency>' \
                      f'    </BkgDetails>' \
                      f'    <To>' \
                      f'        <CountryCode>{order.partner_shipping_id.country_code}</CountryCode>' \
                      f'        <Postalcode>{order.partner_shipping_id.zip}</Postalcode>' \
                      f'        <City>{order.partner_shipping_id.city}</City>' \
                      f'    </To>' \
                      f'</GetQuote>' \
                      f'</ns0:DCTRequest>'

        url = "https://xmlpitest-ea.dhl.com//XMLShippingServlet/DCTRequest"
        headers = {
            'content-type': "application/xml",
            'Content-Length': "0"
        }
        response = requests.post(url, data=xml_request, headers=headers)
        qtd_shp_elements = ET.fromstring(response.text).findall(".//QtdShp")
        vals = {}
        flag = False
        for qtd_shp_element in qtd_shp_elements:
            global_product_code = qtd_shp_element.find("GlobalProductCode")
            shipping_charge = qtd_shp_element.find("ShippingCharge")
            if self.service_type == global_product_code.text.strip():
                vals['success'] = True
                vals['price'] = shipping_charge.text.strip()
                vals['carrier_price'] = vals['price']
                vals['warning_message'] = "Successfully added the DHL Shipping"
                return vals
        if not flag:
            raise UserError(_("There is no service available"))

    def dhl_send_shipping(self, pickings):
        """
           Send a shipping request to DHL for a list of pickings.
           This method creates a shipping order for each picking in the
           provided list and sends it to DHL.
        """
        res = []
        shipping_price = self.create_order(pickings)
        res = res + [{
            'exact_price': float(shipping_price),
            'tracking_number': False
        }]
        return res

    def create_order(self, pickings):
        """
           This function is responsible for creating an order with DHL.
           It should be used when you need to send shipments through DHL.
        """
        shipping_request = ''
        price = 0
        weight = 0
        for rec in pickings.move_line_ids:
            price = price + (rec.quantity * rec.product_id.list_price)
            weight = weight + (rec.quantity * rec.product_id.weight)
            shipping_request = f'<?xml version="1.0" encoding="utf-8"?>' \
                               f'<req:ShipmentRequest schemaVersion="10.0" xmlns:req="http://www.dhl.com">' \
                               f'    <Request>' \
                               f'        <ServiceHeader>' \
                               f'            <MessageTime>{datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")}' \
                               f'</MessageTime>' \
                               f'            <MessageReference>ref:{datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")}' \
                               f'</MessageReference>' \
                               f'            <SiteID>{self.site_id}</SiteID>' \
                               f'            <Password>{self.password}</Password>' \
                               f'        </ServiceHeader>' \
                               f'        <MetaData>' \
                               f'            <SoftwareName>{release.product_name}</SoftwareName>' \
                               f'            <SoftwareVersion>{release.series}</SoftwareVersion>' \
                               f'        </MetaData>' \
                               f'    </Request>' \
                               f'    <RegionCode>AM</RegionCode>' \
                               f'    <RequestedPickupTime>Y</RequestedPickupTime>' \
                               f'    <LanguageCode>en</LanguageCode>' \
                               f'    <Billing>' \
                               f'        <ShipperAccountNumber>{self.account_no}</ShipperAccountNumber>' \
                               f'        <ShippingPaymentType>S</ShippingPaymentType>' \
                               f'        <BillingAccountNumber>None</BillingAccountNumber>' \
                               f'    </Billing>' \
                               f'    <Consignee>' \
                               f'        <CompanyName>{pickings.partner_id.name}</CompanyName>' \
                               f'        <AddressLine1>{pickings.partner_id.street}</AddressLine1>' \
                               f'        <AddressLine2>None</AddressLine2>' \
                               f'        <AddressLine3>None</AddressLine3>' \
                               f'        <City>{pickings.partner_id.city}</City>' \
                               f'        <PostalCode>{pickings.partner_id.zip}</PostalCode>' \
                               f'        <CountryCode>{pickings.partner_id.country_id.code}</CountryCode>' \
                               f'        <CountryName>{pickings.partner_id.country_id.name}</CountryName>' \
                               f'        <Contact>' \
                               f'            <PersonName>{pickings.picking_type_id.warehouse_id.company_id.name}' \
                               f'</PersonName>' \
                               f'            <PhoneNumber>35318746881</PhoneNumber>' \
                               f'            <Email>{pickings.picking_type_id.warehouse_id.company_id.email}</Email>' \
                               f'            <MobilePhoneNumber>None</MobilePhoneNumber>' \
                               f'        </Contact>' \
                               f'        <StreetName>None</StreetName>' \
                               f'        <BuildingName>None</BuildingName>' \
                               f'        <StreetNumber>None</StreetNumber>' \
                               f'        <RegistrationNumbers>' \
                               f'            <RegistrationNumber>' \
                               f'                <Number>None</Number>' \
                               f'                <NumberTypeCode>RGP</NumberTypeCode>' \
                               f'                <NumberIssuerCountryCode>' \
                               f'{pickings.picking_type_id.warehouse_id.company_id.country_id.code}' \
                               f'</NumberIssuerCountryCode>' \
                               f'            </RegistrationNumber>' \
                               f'        </RegistrationNumbers>' \
                               f'    </Consignee>' \
                               f'    <Dutiable>' \
                               f'        <DeclaredValue>72.025</DeclaredValue>' \
                               f'        <DeclaredCurrency>EUR</DeclaredCurrency>' \
                               f'        <ShipperEIN>ShipperEIN</ShipperEIN>' \
                               f'        <TermsOfTrade>DAP</TermsOfTrade>' \
                               f'    </Dutiable>' \
                               f'    <UseDHLInvoice>Y</UseDHLInvoice>' \
                               f'    <DHLInvoiceLanguageCode>en</DHLInvoiceLanguageCode>' \
                               f'    <DHLInvoiceType>CMI</DHLInvoiceType>' \
                               f'    <ExportDeclaration>' \
                               f'        <InvoiceNumber>MyDHLAPI - INV-001</InvoiceNumber>' \
                               f'        <InvoiceDate>{date.today()}</InvoiceDate>' \
                               f'        <ExportLineItem>' \
                               f'            <LineNumber>1</LineNumber>' \
                               f'            <Quantity>1</Quantity>' \
                               f'            <QuantityUnit>PCS</QuantityUnit>' \
                               f'            <Description>{pickings.name}</Description>' \
                               f'            <Value>{price}</Value>' \
                               f'            <IsDomestic>Y</IsDomestic>' \
                               f'            <CommodityCode>123</CommodityCode>' \
                               f'            <Weight>' \
                               f'                <Weight>{weight}</Weight>' \
                               f'                <WeightUnit>K</WeightUnit>' \
                               f'            </Weight>' \
                               f'            <GrossWeight>' \
                               f'                <Weight>{weight}</Weight>' \
                               f'                <WeightUnit>K</WeightUnit>' \
                               f'            </GrossWeight>' \
                               f'            <ManufactureCountryCode>TH</ManufactureCountryCode>' \
                               f'            <ImportCommodityCode>123</ImportCommodityCode>' \
                               f'            <ItemReferences>' \
                               f'                <ItemReference>' \
                               f'                    <ItemReferenceType>AFE</ItemReferenceType>' \
                               f'                    <ItemReferenceNumber>AFE-1299210554413</ItemReferenceNumber>' \
                               f'                </ItemReference>' \
                               f'            </ItemReferences>' \
                               f'            <CustomsPaperworks>' \
                               f'                <CustomsPaperwork>'
        url = "https://xmlpitest-ea.dhl.com//XMLShippingServlet/shipment-validation"
        headers = {
            'content-type': "application/xml",
            'Content-Length': "0"
        }
        response = requests.post(url, data=shipping_request, headers=headers)
        shipping_price = ET.fromstring(response.text).find(
            "ShippingCharge").text
        tracking_number = ET.fromstring(response.text).find(
            "AirwayBillNumber").text
        label = ET.fromstring(response.text).find(
            "LabelImage/OutputImage").text
        pickings.carrier_tracking_ref = tracking_number
        label_attachment = self.env['ir.attachment'].sudo().create({
            'name': 'DHL Shipping Label.pdf',
            'type': 'binary',
            'mimetype': 'application/pdf',
            'datas': label,
            'res_model': 'stock.picking',
            'res_id': pickings.id
        })
        pickings.message_post(
            body="Created Shipment in DHL. Your tracking number is: %s" % tracking_number,
            attachment_ids=[label_attachment.id])
        return shipping_price

    def dhl_get_tracking_link(self, picking):
        """
           This function is used to generate a DHL tracking link for a given
           order's tracking number. It takes the picking parameter, which
           should contain the tracking number for the order, and generates a
           DHL tracking link using the tracking number.
        """
        return 'http://www.dhl.com/en/express/tracking.html?AWB=%s' % picking.carrier_tracking_ref
