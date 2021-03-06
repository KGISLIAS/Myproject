import math
import re
from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
import openerp.addons.decimal_precision as dp
import netsvc
import datetime
import calendar
from datetime import date
import re
import urllib
import urllib2
import logging
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
import calendar
today = datetime.now()

class kg_po_grn(osv.osv):

    def _amount_line_tax(self, cr, uid, line, context=None):
        val = 0.0
        amt_to_per = (line.kg_discount / (line.po_grn_qty * line.price_unit or 1.0 )) * 100
        kg_discount_per = line.kg_discount_per
        tot_discount_per = amt_to_per + kg_discount_per
        for c in self.pool.get('account.tax').compute_all(cr, uid, line.grn_tax_ids,
            line.price_unit * (1-(tot_discount_per or 0.0)/100.0), line.po_grn_qty, line.product_id,
             line.po_grn_id.supplier_id)['taxes']:               
            val += c.get('amount', 0.0)
        return val
    
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        cur_obj=self.pool.get('res.currency')
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'discount' : 0.0,
                'other_charge': 0.0,
            }
            val = val1 = val3 = 0.0
            cur = order.supplier_id.property_product_pricelist_purchase.currency_id
            po_charges=order.value1 + order.value2      
            for line in order.line_ids:
                per_to_amt = (line.po_grn_qty * line.price_unit) * line.kg_discount_per / 100.00
                tot_discount = line.kg_discount + per_to_amt
                val1 += line.price_subtotal
                val += self._amount_line_tax(cr, uid, line, context=context)
                val3 += tot_discount    
            res[order.id]['other_charge']=(round(po_charges,0))
            res[order.id]['amount_tax']=(round(val,0))
            res[order.id]['amount_untaxed']=(round(val1,0))
            #res[order.id]['amount_total']=res[order.id]['amount_untaxed'] + res[order.id]['amount_tax'] 
            res[order.id]['amount_total']=(round(val + val1 + res[order.id]['other_charge'],0))
            res[order.id]['discount']=(round(val3,0))   
        return res
        
    def _get_journal(self, cr, uid, context=None):      
        journal_obj = self.pool.get('account.journal')
        res = journal_obj.search(cr, uid, [('type','=','sale')], limit=1)
        return res and res[0] or False

    def _get_currency(self, cr, uid, context=None):
        res = False
        journal_id = self._get_journal(cr, uid, context=context)
        if journal_id:
            journal = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
            res = journal.currency and journal.currency.id or journal.company_id.currency_id.id
        return res
        
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('po.grn.line').browse(cr, uid, ids, context=context):
            result[line.po_grn_id.id] = True
        return result.keys()
        
    def button_dummy(self, cr, uid, ids, context=None):
        return True 
    
    _name = "kg.po.grn"
    _description = "PO GRN"
    _order = "grn_date desc,name desc"

            
    _columns = {
        
        'created_by':fields.many2one('res.users','Created By',readonly=True),
        'creation_date':fields.datetime('Creation Date',required=True,readonly=True),
        
        'confirmed_by':fields.many2one('res.users','Confirmed By',readonly=True),
        'confirmed_date':fields.datetime('Confirmed Date',readonly=True),
        
        'approved_by':fields.many2one('res.users','Approved By',readonly=True),
        'approved_date':fields.datetime('Approved Date',readonly=True),
        
        'name': fields.char('GRN NO',readonly=True),
        'grn_date':fields.date('GRN Date',required=True,readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
        
        'dc_no': fields.char('DC NO', required=True,readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
        'dc_date':fields.date('DC Date',required=True, readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
        
        'po_id':fields.many2one('purchase.order', 'PO NO',
                    domain="[('state','=','approved'), '&', ('order_line.pending_qty','>','0'), '&', ('grn_flag','=',False), '&', ('partner_id','=',supplier_id), '&', ('order_line.line_state','!=','cancel')]"), 
        
        'po_ids':fields.many2many('purchase.order', 'multiple_po', 'grn_id', 'po_id', 'PO Nos',
                    domain="[('state','=','approved'), '&', ('order_line.pending_qty','>','0'), '&', ('grn_flag','=',False), '&', ('partner_id','=',supplier_id), '&', ('order_line.line_state','!=','cancel')]"), 
        
        'po_name': fields.char('PO NO',readonly=True),
        
        'order_no': fields.char('Order NO',readonly=True),
        
        'order_date': fields.char('Order Date',readonly=True),
        
        'pos_date': fields.char('PO Date',readonly=True),
        
        'po_date':fields.date('PO Date',readonly=True),
        
        'supplier_id':fields.many2one('res.partner','Supplier',domain=[('supplier','=',True)],required=True),
        
        'billing_status': fields.selection([
            ('applicable', 'Applicable'),
            ('not_applicable', 'Not Applicable')], 'Billing Status',required=True,readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
        
        'inward_type': fields.many2one('kg.inwardmaster', 'Inward Type',readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
        
        'line_ids':fields.one2many('po.grn.line','po_grn_id','Line Entry',readonly=False, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
        
        'department_id': fields.many2one('kg.depmaster','Department',readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
        
        'state': fields.selection([('item_load','Draft'),('draft', 'Waiting for Confirmation'), ('confirmed', 'Waiting for Approval'), ('done', 'Done'), ('inv', 'Invoiced'), ('cancel', 'Cancelled'),('reject','Rejected')], 'Status',readonly=True),
        
        'type': fields.selection([('in', 'IN'), ('out', 'OUT'), ('internal', 'Internal')], 'Type'),
        
        'active':fields.boolean('Active'),
        
        'remark':fields.text('Remarks'),
        'po_so_remark':fields.text('PO/SO Remarks'),
        
        'confirm_flag':fields.boolean('Confirm Flag'),
        'approve_flag':fields.boolean('Expiry Flag'),
        'bill_flag':fields.boolean('Bill Flag'),
        'invoice_flag':fields.boolean('Invoice Flag'),
        'company_id':fields.many2one('res.company','Company'),

        'other_charge': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Other Charges(+)',
             multi="sums", help="The amount without tax", track_visibility='always'),       
        
        'discount': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Total Discount(-)',
            store={
                'kg.po.grn': (lambda self, cr, uid, ids, c={}: ids, ['line_ids'], 10),
                'po.grn.line': (_get_order, ['price_unit', 'grn_tax_ids', 'kg_discount', 'po_grn_qty'], 10),
            }, multi="sums", help="The amount without tax", track_visibility='always'),
        'amount_untaxed': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'kg.po.grn': (lambda self, cr, uid, ids, c={}: ids, ['line_ids'], 10),
                'po.grn.line': (_get_order, ['price_unit', 'grn_tax_ids', 'kg_discount', 'po_grn_qty'], 10),
            }, multi="sums", help="The amount without tax", track_visibility='always'),
        'amount_tax': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Taxes',
            store={
                'kg.po.grn': (lambda self, cr, uid, ids, c={}: ids, ['line_ids'], 10),
                'po.grn.line': (_get_order, ['price_unit', 'grn_tax_ids', 'kg_discount', 'po_grn_qty'], 10),
            }, multi="sums", help="The tax amount"),
        'amount_total': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Total',
            store=True,multi="sums",help="The total amount"),
        'pricelist_id':fields.many2one('product.pricelist', 'Pricelist'),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
        'po_expenses_type1': fields.selection([('freight','Freight Charges'),('others','Others')], 'Expenses Type1', 
                                        readonly=True),
        'po_expenses_type2': fields.selection([('freight','Freight Charges'),('others','Others')], 'Expenses Type2', 
                                readonly=True),
        'value1':fields.float('Value1', readonly=True),
        'value2':fields.float('Value2', readonly=True),
        
        'grn_type': fields.selection([('from_po','Purchase Order'),('from_so','Service Order'),('from_gp','Gate Pass')], 'GRN From', 
                                        required=True, readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),                 
        
        
        'grn_dc': fields.selection([('dc_invoice','DC & Invoice'),('only_grn','Only grn')], 'GRN Type', 
                                        required=True, readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),                 
    
        
                                        
        'so_id':fields.many2one('kg.service.order', 'SO NO',
                    domain="[('state','=','approved'), '&', ('service_order_line.pending_qty','>','0'), '&', ('grn_flag','=',False), '&', ('partner_id','=',supplier_id),'&',('so_type','=','service')]"), 
        'so_ids':fields.many2many('kg.service.order', 'multiple_so', 'grn_id', 'so_id', 'SO NO',
                    domain="[('state','=','approved'), '&', ('service_order_line.pending_qty','>','0'), '&', ('grn_flag','=',False), '&', ('partner_id','=',supplier_id),'&',('so_type','=','service')]"), 
        
        'gp_line_ids':fields.many2many('kg.gate.pass.line', 'multiple_gp', 'grn_id', 'gp_line_id', 'Gate Pass No',
                    domain="[('gate_id.state','=','done'), '&', ('grn_pending_qty','>','0'), '&', ('so_flag','=',False)]"), 
        
        
        'gp_ids':fields.many2many('kg.gate.pass', 'multiple_gate', 'grn_id', 'gp_id', 'Gate Pass No',
                    domain="[('state','=','done'), '&', ('gate_line.grn_pending_qty','>','0'), '&', ('gate_line.so_flag','=',False),'&', ('partner_id','=',supplier_id)]"), 
        
        
        
        'so_date':fields.date('SO Date',readonly=True),
        
        'so_name': fields.char('SO NO',readonly=True),
        
        
        'gp_date':fields.date('GP Date',readonly=True),
        
        'gp_name': fields.char('GP NO',readonly=True),
        
        
        
        'sos_date': fields.char('SO Date',readonly=True),
        
        'payment_type': fields.selection([('cash', 'Cash'), ('credit', 'Credit')], 'Payment Type',required=True, readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
        'dep_project':fields.many2one('kg.project.master','Dept/Project Name',readonly=False,states={'readonly': [('readonly', True)]}),    
        'reject_remark':fields.text('Cancel Remarks', readonly=True, states={'confirmed':[('readonly',False)]}),
    
    
        'sup_invoice_no':fields.char('Supplier Invoice No',size=200, readonly=False, states={'done':[('readonly',True)]}),
        'sup_invoice_date':fields.date('Supplier Invoice Date', readonly=False, states={'done':[('readonly',True)]}),
        
    
    }
    
    _defaults = {
        
        'creation_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'grn_date': fields.date.context_today,
        'created_by': lambda obj, cr, uid, context: uid,
        'state':'item_load',
        'type':'in',
        'name':'',
        'billing_status':'applicable',
        'active':True,
        'confirm_flag':False,
        'approve_flag':False,
        'company_id' : lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.po.grn', context=c),
        #'payment_type':'credit',
        #'grn_dc':'only_grn',
    }
    
    ### Back Entry Date ###
        
    def email_ids(self,cr,uid,ids,context = None):
        email_from = []
        email_to = []
        email_cc = []
        val = {'email_from':'','email_to':'','email_cc':''}
        ir_model = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
        mail_form_ids = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
        for ids in mail_form_ids:
            mail_form_rec = self.pool.get('kg.mail.settings').browse(cr,uid,ids)
            if mail_form_rec.doc_name.model == 'kg.po.grn':
                email_from.append(mail_form_rec.name)
                mail_line_id = self.pool.get('kg.mail.settings.line').search(cr,uid,[('line_entry','=',ids)])
                for mail_id in mail_line_id:
                    mail_line_rec = self.pool.get('kg.mail.settings.line').browse(cr,uid,mail_id)
                    if mail_line_rec.to_address:
                        email_to.append(mail_line_rec.mail_id)
                    if mail_line_rec.cc_address:
                        email_cc.append(mail_line_rec.mail_id)
                        
            else:
                pass           
        val['email_from'] = email_from
        val['email_to'] = email_to
        val['email_cc'] = email_cc
        return val   
       
    def onchange_grn_date(self, cr, uid, ids, grn_date):
        print "kgggggggggggggggggg --  grn_date called"
        today_date = today.strftime('%Y-%m-%d')
        back_list = []
        today_new = today.date()
        print "---------------------------->",today_new
        bk_date = date.today() - timedelta(days=3)
        back_date = bk_date.strftime('%Y-%m-%d')
        
        d1 = today_new
        d2 = bk_date

        delta = d1 - d2

        for i in range(delta.days + 1):
            bkk_date = d1 - timedelta(days=i)
            backk_date = bkk_date.strftime('%Y-%m-%d')
            back_list.append(backk_date)
        holiday_obj = self.pool.get('kg.holiday.master.line')
        holiday_ids = holiday_obj.search(cr, uid, [('leave_date','in',back_list)])
        if grn_date > today_date:
            raise osv.except_osv(
                    _('Warning'),
                    _('GRN Date should be less than or equal to current date!'))
        if holiday_ids:
            hol_bk_date = date.today() - timedelta(days=(3+len(holiday_ids)))
            hol_back_date = hol_bk_date.strftime('%Y-%m-%d')
            if grn_date < hol_back_date:
                raise osv.except_osv(
                    _('Warning'),
                    _('GRN Entry is not allowed for this date!'))
        elif (x for x in back_list if calendar.day_name[x.weekday()]  == 'Sunday'):         
            hol_bk_date = date.today() - timedelta(days=4)
            hol_back_date = hol_bk_date.strftime('%Y-%m-%d')
            if grn_date < hol_back_date:
                raise osv.except_osv(
                    _('Warning'),
                    _('GRN Entry is not allowed for this date!'))
        else:
            if grn_date <= back_date:
                raise osv.except_osv(
                    _('Warning'),
                    _('GRN Entry is not allowed for this date!'))
        return True
    
    # Onchange PO Date #
    
    def onchange_po_id(self, cr, uid, ids, po_ids, context=None):
        value = {'po_date': today,'po_so_remark':''}
        if len(po_ids) > 1:
            po_rec = self.pool.get('purchase.order').browse(cr, uid, po_ids[0][2][0], context=context)
            value = {'po_date': po_rec.date_order,'po_so_remark':po_rec.dep_project_name}
            print po_rec.date_order
        return {'value': value}
        
    # Onchange SO Date #
        
    def onchange_so_id(self, cr, uid, ids, so_ids, context=None):        
        value = {'so_date': today,'po_so_remark':''}
        print so_ids[0][2][0]
        if so_ids[0][2][0]:
            so_rec = self.pool.get('kg.service.order').browse(cr, uid, so_ids[0][2][0], context=context)
            value = {'so_date': so_rec.date,'po_so_remark':so_rec.origin}
            print so_rec.date
        return {'value': value}        
    
    def onchange_user_id(self, cr, uid, ids, created_by, context=None):        
        value = {'department_id': ''}
        if created_by:
            user = self.pool.get('res.users').browse(cr, uid, created_by, context=context)
            value = {'department_id': user.dep_name.id}
        return {'value': value}

    def onchange_partner_id(self, cr, uid, ids, supplier_id):
        partner = self.pool.get('res.partner')      
        supplier_address = partner.address_get(cr, uid, [supplier_id], ['default'])
        supplier = partner.browse(cr, uid, supplier_id)
        return {'value': {
            'pricelist_id': supplier.property_product_pricelist_purchase.id,
            }}
    
    # Create Method #
    """
    def create(self, cr, uid, vals,context=None):
        print "vals..............................",vals 
        if vals.get('name',False)==False:
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'kg.po.grn') or False
        grn =  super(kg_po_grn, self).create(cr, uid, vals, context=context)
        return grn
    """
    
    # Reject Method #
    
    def grn_reject(self, cr, uid, ids, context=None):
        grn = self.browse(cr, uid, ids[0])
        po_id = self.pool.get('purchase.order')
        so_id = self.pool.get('kg.service.order')
        print "grn........................", grn
        if not grn.reject_remark:
            raise osv.except_osv(_('Remarks is must !!'), _('Enter Remarks for GRN Rejection !!!'))
        else:
            self.write(cr, uid, ids[0], {'state' : 'draft'})
        for line in grn.grn_line:
            if grn.grn_type == 'from_po':
                po_id.write(cr, uid, line.po_line_id.order_id.id, {'grn_flag' : False})
            if grn.grn_type == 'from_so':
                so_id.write(cr, uid, line.so_line_id.service_id.id, {'grn_flag' : False})   
            
        return True     

    # Delete Method #

    def unlink(self, cr, uid, ids, context=None):
        unlink_ids = []             
        grn_rec = self.browse(cr, uid, ids[0])
        if grn_rec.state != 'draft':
            raise osv.except_osv(_('Invalid action !'), _('System not allow to delete Confirmed and Done state GRN !!'))
        else:
            unlink_ids.append(grn_rec.id)
        return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
        
    # GRN LINE Creation #
        
    def update_potogrn(self,cr,uid,ids,picking_id=False,context={}):
        ### PO TO GRN ####
        self.write(cr,uid,ids[0],{'state':'draft'})
        po_id = False
        grn_entry_obj = self.browse(cr,uid,ids[0])
        if grn_entry_obj.grn_type == 'from_po':
            cr.execute(""" select po_id from multiple_po where grn_id = %s """ %(grn_entry_obj.id))
            po_data = cr.dictfetchall()
            po_obj=self.pool.get('purchase.order')
            po_grn_obj=self.pool.get('kg.po.grn')
            po_grn_line_obj=self.pool.get('po.grn.line')
            pol_obj = self.pool.get('purchase.order.line')
            #po_order = grn_entry_obj.po_id
            line_ids = map(lambda x:x.id,grn_entry_obj.line_ids)
            po_grn_line_obj.unlink(cr,uid,line_ids)
            value1 = 0
            value2 = 0
            po_list = []
            podate_list = []
            poremark_list = []
            for item in po_data:
                po_id = item['po_id']
                po_record = po_obj.browse(cr, uid, po_id)
                po_list.append(po_record.name)
                date_order = po_record.date_order
                date_order = datetime.strptime(date_order, '%Y-%m-%d')
                date_order = date_order.strftime('%d/%m/%Y')
                podate_list.append(date_order)
                po_name = ",".join(po_list)
                po_date = ",".join(podate_list)
                if po_record.dep_project_name:
                    poremark_list.append(po_record.dep_project_name)
                    po_remark = ",".join(poremark_list)
                else:
                    po_remark = ""  
                po_expenses_type1 = po_record.po_expenses_type1 
                po_expenses_type2 = po_record.po_expenses_type2 
                value1 += po_record.value1 or 0
                value2 += po_record.value2 or 0
                self.write(cr,uid,ids[0],{
                            'order_no':po_name,
                            'order_date':po_date,
                            'po_expenses_type1':po_expenses_type1,
                            'po_expenses_type2':po_expenses_type2,
                            'value1':value1,
                            'value2':value2,
                            'po_so_remark':po_remark,
                            })
                po_grn_id = grn_entry_obj.id
                order_lines=po_record.order_line
                for order_line in order_lines:
                    if order_line.pending_qty > 0 and order_line.line_state != 'cancel':
                        po_grn_line_obj.create(cr, uid, {
                            'name': order_line.product_id.name or '/',
                            'product_id': order_line.product_id.id,
                            'brand_id':order_line.brand_id.id,
                            'po_grn_qty': order_line.pending_qty,
                            'po_qty':order_line.product_qty,
                            'po_pending_qty':order_line.pending_qty,
                            'uom_id': order_line.product_uom.id,
                            'po_id': order_line.order_id.id,
                            'location_id': po_record.partner_id.property_stock_supplier.id,
                            'location_dest_id': po_record.location_id.id,
                            'po_grn_id': po_grn_id,
                            'state': 'confirmed',
                            'po_line_id': order_line.id,
                            'price_unit': order_line.price_unit,
                            'pi_line_id':order_line.pi_line_id.id,
                            'grn_tax_ids': [(6, 0, [x.id for x in order_line.taxes_id])],
                            'kg_discount_per':order_line.kg_discount_per,
                            'kg_discount': order_line.kg_discount,
                            'po_grn_date':grn_entry_obj.grn_date,
                            'po_flag':'True',
                            'billing_type':'cost',
                            'order_no': order_line.order_id.name,
                            'order_date': order_line.order_id.date_order,
                        })
                    else:
                        print "NO Qty or Cancel"
        if grn_entry_obj.grn_type == 'from_so':     
                
            ### SO TO GRN ####
        
            so_id = False
            
            cr.execute(""" select so_id from multiple_so where grn_id = %s """ %(grn_entry_obj.id))
            so_data = cr.dictfetchall()
            so_obj=self.pool.get('kg.service.order')
            po_grn_obj=self.pool.get('kg.po.grn')
            po_grn_line_obj=self.pool.get('po.grn.line')
            sol_obj = self.pool.get('kg.service.order.line')
            #so_order = grn_entry_obj.so_id
            line_ids = map(lambda x:x.id,grn_entry_obj.line_ids)
            po_grn_line_obj.unlink(cr,uid,line_ids)
            value1 = 0
            value2 = 0
            so_list = []
            sodate_list = []
            soremark_list = []
            for item in so_data:
                so_id = item['so_id']
                so_record = so_obj.browse(cr, uid, so_id)
                so_list.append(so_record.name)
                date_order = so_record.date
                date_order = datetime.strptime(date_order, '%Y-%m-%d')
                date_order = date_order.strftime('%d/%m/%Y')
                sodate_list.append(date_order)
                soremark_list.append(so_record.origin)
                so_name = ",".join(so_list)
                so_date = ",".join(sodate_list)
                so_remark = ",".join(soremark_list)
                po_expenses_type1 = so_record.po_expenses_type1 
                po_expenses_type2 = so_record.po_expenses_type2 
                value1 += so_record.value1 or 0
                value2 += so_record.value2 or 0
                self.write(cr,uid,ids[0],{
                            'order_no':so_name,
                            'order_date':so_date,
                            'po_expenses_type1':po_expenses_type1,
                            'po_expenses_type2':po_expenses_type2,
                            'value1':value1,
                            'value2':value2,
                            'po_so_remark':so_remark,
                            })
                po_grn_id = grn_entry_obj.id
                order_lines=so_record.service_order_line
                for order_line in order_lines:
                    if order_line.pending_qty > 0 and order_line.state != 'cancel':
                        po_grn_line_obj.create(cr, uid, {
                            'name': order_line.product_id.name or '/',
                            'product_id': order_line.product_id.id,
                            'brand_id':order_line.brand_id.id,
                            'po_grn_qty': order_line.pending_qty,
                            'so_qty':order_line.product_qty,
                            'so_pending_qty':order_line.pending_qty,
                            'uom_id': order_line.product_uom.id,
                            'location_id': so_record.partner_id.property_stock_supplier.id,
                            #'location_dest_id': so_order.location_id.id,
                            'po_grn_id': po_grn_id,
                            'state': 'confirmed',
                            'so_line_id': order_line.id,
                            'so_id': order_line.service_id.id,
                            'price_unit': order_line.price_unit,
                            'si_line_id':order_line.soindent_line_id.id,
                            'grn_tax_ids': [(6, 0, [x.id for x in order_line.taxes_id])],
                            'kg_discount_per':order_line.kg_discount_per,
                            'kg_discount': order_line.kg_discount,
                            'po_grn_date':grn_entry_obj.grn_date,
                            'so_flag':'True',
                            'billing_type':'cost',
                            'ser_no':order_line.ser_no,
                            'serial_no':order_line.serial_no.id,
                            'order_no': order_line.service_id.name,
                            'order_date': order_line.service_id.date,
                        })
                        
                    else:
                        print "NO Qty or Cancel"
                        
                        
        if grn_entry_obj.grn_type == 'from_gp':     
            
            cr.execute(""" select gp_id from multiple_gate where grn_id = %s """ %(grn_entry_obj.id))
            gp_data = cr.dictfetchall()
            gp_obj=self.pool.get('kg.gate.pass')
            po_grn_obj=self.pool.get('kg.po.grn')
            po_grn_line_obj=self.pool.get('po.grn.line')
            gpl_obj = self.pool.get('kg.gate.pass.line')
            #so_order = grn_entry_obj.so_id
            line_ids = map(lambda x:x.id,grn_entry_obj.line_ids)
            po_grn_line_obj.unlink(cr,uid,line_ids)
            value1 = 0
            value2 = 0
            gp_list = []
            gpdate_list = []
            for item in gp_data:
                gp_id = item['gp_id']
                gp_record = gp_obj.browse(cr, uid, gp_id)
                gp_list.append(gp_record.name)
                date_order = gp_record.date
                date_order = date_order.strftime('%d/%m/%Y')
                gpdate_list.append(date_order)
                gp_name = ",".join(gp_list)
                gp_date = ",".join(gpdate_list)
                self.write(cr,uid,ids[0],{
                            'order_no':gp_name,
                            'order_date':gp_date,
                            })
                po_grn_id = grn_entry_obj.id
                order_lines=gp_record.gate_line
                for order_line in order_lines:
                    if order_line.grn_pending_qty > 0 and order_line.state != 'cancel':
                        po_grn_line_obj.create(cr, uid, {
                            'name': order_line.product_id.name or '/',
                            'product_id': order_line.product_id.id,
                            'brand_id':order_line.brand_id.id,
                            'po_grn_qty': order_line.grn_pending_qty,
                            'gp_qty':order_line.qty,
                            'gp_pending_qty':order_line.grn_pending_qty,
                            'uom_id': order_line.uom.id,
                            'location_id': order_line.gate_id.partner_id.property_stock_supplier.id,
                            #'location_dest_id': so_order.location_id.id,
                            'po_grn_id': po_grn_id,
                            'state': 'confirmed',
                            'gp_line_id': order_line.id,
                            'price_unit': 0,
                            #'si_line_id':order_line.soindent_line_id.id,
                            #'grn_tax_ids': [(6, 0, [x.id for x in order_line.taxes_id])],
                            #'kg_discount_per':order_line.kg_discount_per,
                            #'kg_discount': order_line.kg_discount,
                            'po_grn_date':grn_entry_obj.grn_date,
                            'gp_flag':'True',
                            'billing_type':'free',
                            'ser_no':order_line.ser_no,
                            'serial_no':order_line.serial_no.id,
                            'order_no': order_line.gate_id.name,
                            'order_date': order_line.gate_id.date,
                        })
                    else:
                        print "NO Qty or Cancel"                                

        return True
    
    # PO GRN Confirm #
        
    def po_grn_confirm(self, cr, uid, ids,context=None):
        back_list = []
        grn_entry = self.browse(cr, uid, ids[0])
        po_obj=self.pool.get('purchase.order')
        so_obj=self.pool.get('kg.service.order')
        #if grn_entry.grn_type == 'from_po':
            #po_obj.write(cr,uid,grn_entry.po_id.id, {'grn_flag': True})
        #if grn_entry.grn_type == 'from_so':    
            #so_obj.write(cr,uid,grn_entry.so_id.id, {'grn_flag': True})
        exp_grn_qty = 0
        grn_date = grn_entry.grn_date
        today_date = today.strftime('%Y-%m-%d')
        back_list = []
        today_new = today.date()
        print "---------------------------->",today_new
        bk_date = date.today() - timedelta(days=3)
        back_date = bk_date.strftime('%Y-%m-%d')
        
        d1 = today_new
        d2 = bk_date

        delta = d1 - d2

        for i in range(delta.days + 1):
            bkk_date = d1 - timedelta(days=i)
            backk_date = bkk_date.strftime('%Y-%m-%d')
            back_list.append(backk_date)
        print "---------------------------->",back_list
        
        holiday_obj = self.pool.get('kg.holiday.master.line')
        holiday_ids = holiday_obj.search(cr, uid, [('leave_date','in',back_list)])
        print "holiday_ids........dcwedwed.......",holiday_ids
        
        
        if grn_date > today_date:
            raise osv.except_osv(
                    _('Warning'),
                    _('GRN Date should be less than or equal to current date!'))
                        
                    
        
                    
        if holiday_ids:
            hol_bk_date = date.today() - timedelta(days=(3+len(holiday_ids)))
            hol_back_date = hol_bk_date.strftime('%Y-%m-%d')
            if grn_date < hol_back_date:
                raise osv.except_osv(
                    _('Warning'),
                    _('GRN Entry is not allowed for this date!'))
        elif (x for x in back_list if calendar.day_name[x.weekday()]  == 'Sunday'):      
            hol_bk_date = date.today() - timedelta(days=4)
            hol_back_date = hol_bk_date.strftime('%Y-%m-%d')
            print "-------------------------------hai>"
            if grn_date < hol_back_date:
                raise osv.except_osv(
                    _('Warning'),
                    _('GRN Entry is not allowed for this date!'))

        else:
            if grn_date < back_date:
                raise osv.except_osv(
                    _('Warning'),
                    _('GRN Entry is not allowed for this date!'))
        if grn_entry.name == '':
            grn_no = self.pool.get('ir.sequence').get(cr, uid, 'kg.po.grn')
            self.write(cr,uid,ids,{'name':grn_no})
            print "grn_no...........",grn_no
        
        if grn_entry.dc_date and grn_entry.dc_date > grn_entry.grn_date:
            raise osv.except_osv(_('DC Date Error!'),_('DC Date Should Be Less Than GRN Date.'))            
        if not grn_entry.line_ids:
            raise osv.except_osv(_('Item Line Empty!'),_('You cannot process GRN without Item Line.'))
        
        
            
        for line in grn_entry.line_ids:
            
            if line.inward_type.id == False:
                raise osv.except_osv(_('Warning!'), _('Kindly Give Inward Type for %s !!' %(line.product_id.name)))
            
            if line.billing_type == 'cost':
            
                if grn_entry.grn_type == 'from_po':
                    po_obj.write(cr,uid,line.po_line_id.order_id.id, {'grn_flag': True})
                    if line.po_grn_qty > line.po_pending_qty:
                        raise osv.except_osv(_('Warning!'), _('GRN Qty should not be greater than PO Qty for %s !!' %(line.product_id.name)))
                        
                if grn_entry.grn_type == 'from_so':
                    so_obj.write(cr,uid,line.so_line_id.service_id.id, {'grn_flag': True})
                    if line.po_grn_qty > line.so_pending_qty:
                        raise osv.except_osv(_('Warning!'), _('GRN Qty should not be greater than SO Qty for %s !!' %(line.product_id.name)))
                        
            
            product_id = line.product_id.id
            product_rec = self.pool.get('product.product').browse(cr, uid, product_id)
            if product_rec.expiry == True:
                if not line.po_exp_id:
                    raise osv.except_osv(_('Warning!'), _('You should specify expiry date and batch no for %s !!' %(line.product_id.name)))  
            
            if line.po_exp_id:
                for exp_line in line.po_exp_id:
                    if line.po_grn_date > exp_line.exp_date:
                        raise osv.except_osv(
                                _('Expiry Date Should Not Be Less Than Current Date!'),
                                _('Change the product expity date to greater than current date for Product %s' %(line.product_id.name)))
                                
                                
                cr.execute(""" select sum(product_qty) from kg_po_exp_batch where po_grn_line_id = %s """ %(line.id))
                exp_data = cr.dictfetchone()
                        
                exp_grn_qty = exp_data['sum']
                print "exp_grn_qty",exp_grn_qty,line.product_id.name    
                if exp_grn_qty > line.po_grn_qty:
                    raise osv.except_osv(_('Please Check!'), _('Quantity specified in Batch Details should not exceed than GRN Quantity for %s!!'%(line.product_id.name)))
                    
                if exp_grn_qty < line.po_grn_qty:
                    raise osv.except_osv(_('Please Check!'), _('Quantity specified in Batch Details should not less than GRN Quantity for %s!!'%(line.product_id.name)))
                    
                        
            if line.po_grn_qty == 0:
                    raise osv.except_osv(
                    _('Item Qty can not Zero!'),
                    _('You cannot process GRN with Item Line Qty Zero for Product %s.' %(line.product_id.name)))
            #Write a tax amount in line
            product_tax_amt = self._amount_line_tax(cr, uid, line, context=context)
            cr.execute("""update po_grn_line set product_tax_amt = %s where id = %s"""%(product_tax_amt,line.id))
        self.write(cr,uid,ids[0],{'state':'confirmed',
                                  'confirm_flag':'False',
                                  'confirmed_by':uid,
                                  'confirmed_date':today,
                                   })
        cr.execute("""select all_transaction_mails('PO/SO GRN Approval',%s)"""%(ids[0]))
        data = cr.fetchall();
        vals = self.email_ids(cr,uid,ids,context = context)
        if (not vals['email_to']) or (not vals['email_cc']):
            pass
        else:
            ir_mail_server = self.pool.get('ir.mail_server')
            msg = ir_mail_server.build_email(
                    email_from = vals['email_from'][0],
                    email_to = vals['email_to'],
                    subject = " PO/SO GRN - Waiting For Approval",
                    body = data[0][0],
                    email_cc = vals['email_cc'],
                    object_id = ids[0] and ('%s-%s' % (ids[0], 'kg.po.grn')),
                    subtype = 'html',
                    subtype_alternative = 'plain')
            res = ir_mail_server.send_email(cr, uid, msg,mail_server_id=1, context=context)                  
        
        return True
        
        
        
        # PO GRN APPROVE #
        
    def kg_po_grn_approve(self, cr, uid, ids,context=None):
        user_id = self.pool.get('res.users').browse(cr, uid, uid)
        grn_entry = self.browse(cr, uid, ids[0])
        gate_obj = self.pool.get('kg.gate.pass')
        if grn_entry.confirmed_by.id == uid:
            raise osv.except_osv(
                    _('Warning'),
                    _('Approve cannot be done by Confirmed user'))
        else:
            lot_obj = self.pool.get('stock.production.lot')
            stock_move_obj=self.pool.get('stock.move')
            dep_obj = self.pool.get('kg.depmaster')
            po_line_obj = self.pool.get('purchase.order.line')
            po_obj = self.pool.get('purchase.order')
            so_line_obj = self.pool.get('kg.service.order.line')
            so_obj = self.pool.get('kg.service.order')
            gp_line_obj = self.pool.get('kg.gate.pass.line')
            gp_obj = self.pool.get('kg.gate.pass')
            pi_obj = self.pool.get('kg.purchase.invoice')
            pi_po_grn_obj = self.pool.get('kg.pogrn.purchase.invoice.line')
            po_order = grn_entry.po_id
            dep_id = user_id.dep_name.id
            dep_record = dep_obj.browse(cr,uid,dep_id)
            dest_location_id = dep_record.main_location.id 
            line_tot = 0            
            line_id_list = []
            if grn_entry.grn_dc == 'dc_invoice' and grn_entry.grn_type != 'from_gp':
                partner = self.pool.get('res.partner')
                supplier = partner.browse(cr, uid, grn_entry.supplier_id.id)
                tot_add = (supplier.street or '')+ ' ' + (supplier.street2 or '') + '\n'+(supplier.city.name or '')+ ',' +(supplier.state_id.name or '') + '-' +(supplier.zip or '') + '\nPh:' + (supplier.phone or '')+ '\n' +(supplier.mobile or '')
                if grn_entry.grn_type == 'from_po':
                    grn_type = 'from_po'
                if grn_entry.grn_type == 'from_so':
                    grn_type = 'from_so'    
                invoice_no = pi_obj.create(cr, uid, {
                            'created_by': uid,
                            'creation_date': today,
                            'type':grn_type,
                            'purpose': 'consu',
                            'grn_type':'from_po_grn',
                            'supplier_id':grn_entry.supplier_id.id,
                            'sup_address': tot_add,
                            'sup_invoice_date' : today,
                            'sup_invoice_no':grn_entry.sup_invoice_no,
                            'sup_invoice_date':grn_entry.sup_invoice_date,
                        })
                sql1 = """ insert into purchase_invoice_grn_ids(invoice_id,grn_id) values(%s,%s)"""%(invoice_no,grn_entry.id)
                cr.execute(sql1)
            for line in grn_entry.line_ids:
                line_id = line.id
                brand = []
                if line.brand_id:
                    brand.append("brand_id = %s"%(line.brand_id.id))
                if brand:
                    brand = 'and ('+' or '.join(brand)
                    brand =  brand+')'
                else:
                    brand = ''
                print "branddddddd",brand,type(brand)
                sql = """select * from stock_move where product_id="""+str(line.product_id.id)+""" and move_type='in' """+ brand +""" and po_grn_line_id="""+str(line.id)+""" and price_unit="""+str(line.price_unit)+""" """
                cr.execute(sql)
                data = cr.dictfetchall()
                if data:
                    del_sql = """delete from stock_move where product_id="""+str(line.product_id.id)+""" and move_type='in'  """+ brand +"""  and po_grn_line_id="""+str(line.id)+""" and price_unit="""+str(line.price_unit)+""" """
                    cr.execute(del_sql)
                    
                sql1 = """select * from stock_production_lot where lot_type='in' """+ brand +""" and product_id="""+str(line.product_id.id)+""" and grn_no='"""+str(line.po_grn_id.name)+"""' and price_unit="""+str(line.price_unit)+""" """
                cr.execute(sql1)
                data1 = cr.dictfetchall()
                if data1:
                    del_sql1 = """delete from stock_production_lot where lot_type='in' """+ brand +""" and product_id="""+str(line.product_id.id)+""" and grn_no='"""+str(line.po_grn_id.name)+"""' and price_unit="""+str(line.price_unit)+""" """
                    cr.execute(del_sql1)
                    
                print data1
                if grn_entry.grn_type == 'from_po':
                    
                    #po_id = grn_entry.po_id.id
                    #po_obj.write(cr,uid,po_id, {'grn_flag':False})
                    if line.po_line_id.order_id:
                        po_obj.write(cr,uid,line.po_line_id.order_id.id, {'grn_flag': False})
                    
                    if line.billing_type == 'cost':
                
                        if line.po_grn_qty > line.po_pending_qty:
                            raise osv.except_osv(_('Warning!'), _('GRN Qty should not be greater than PO Qty for %s !!' %(line.product_id.name)))
                    # This code is to update pending qty in Purchase Order #
                    
                    rec_qty = line.po_line_id.received_qty
                    pending_qty = line.po_line_id.pending_qty
                    if line.po_line_id:
                        po_line_id = line.po_line_id
                        grn_qty = line.po_grn_qty
                        po_line_qty = line.po_qty
                        po_line_pending_qty = pending_qty - grn_qty
                        rec_qty += line.po_grn_qty
                        print "po_line_id :", po_line_id, "=====================po_qty", po_line_pending_qty
                        po_line_obj.write(cr, uid, [line.po_line_id.id],
                                {
                                'pending_qty' : po_line_pending_qty,
                                'received_qty' : rec_qty,
                                })
                                
                if grn_entry.grn_type == 'from_so':
                    
                    so_id = grn_entry.so_id.id
                    so_obj.write(cr,uid,so_id, {'grn_flag':False})
                    so_obj.write(cr,uid,line.so_line_id.service_id.id, {'grn_flag': False})
                    
                    if line.billing_type == 'cost':
                    
                        if line.po_grn_qty > line.so_pending_qty:
                            raise osv.except_osv(_('Warning!'), _('GRN Qty should not be greater than SO Qty for %s !!' %(line.product_id.name)))
                    # This code is to update pending qty in Service Order #
                    
                    rec_qty = line.so_line_id.received_qty
                    print "rec_qty.............",rec_qty
                    pending_qty = line.so_line_id.pending_qty
                    if line.so_line_id:
                        so_line_id = line.so_line_id
                        grn_qty = line.po_grn_qty
                        so_line_qty = line.so_qty
                        so_line_pending_qty = pending_qty - grn_qty
                        rec_qty += line.po_grn_qty
                        print "so_line_id :", so_line_id, "=====================so_qty", so_line_pending_qty,rec_qty
                        so_line_obj.write(cr, uid, [line.so_line_id.id],
                                {
                                'pending_qty' : so_line_pending_qty,
                                'received_qty' : rec_qty,
                                })
                    
                if grn_entry.grn_type == 'from_gp':
                    
                                        
                    if line.po_grn_qty > line.gp_pending_qty:
                        raise osv.except_osv(_('Warning!'), _('GRN Qty should not be greater than GP Qty for %s !!' %(line.product_id.name)))
                    
                        
                    # This code is to update pending qty in Gate Pass #
                    
                    
                    if line.gp_line_id:
                        
                        pending_qty = line.gp_line_id.grn_pending_qty
                        grn_qty = line.po_grn_qty
                        
                        gp_line_pending_qty = pending_qty - grn_qty
                        #rec_qty += line.po_grn_qty
                        
                        if gp_line_pending_qty > 0:
                            status = 'pending'
                        else:
                            status = 'done'
                            
                        gp_obj.write(cr, uid, [line.gp_line_id.gate_id.id],
                                {
                                
                                'in_state' : status
                                
                                })
                        gp_line_obj.write(cr, uid, [line.gp_line_id.id],
                                {
                                'grn_pending_qty' : gp_line_pending_qty,
                                
                                
                                })
                                            
                            
                # This code will create PO GRN to Stock Move
                
                # UOM Checking #
                
                if grn_entry.grn_type == 'from_po':
                    
                    if line.billing_type == 'cost':
                
                        if line.uom_id.id != line.product_id.uom_id.id:
                            product_uom = line.product_id.uom_id.id
                            po_coeff = line.product_id.po_uom_coeff
                            product_qty = line.po_grn_qty * po_coeff
                            price_unit =  line.po_line_id.price_subtotal / product_qty
                                
                        elif line.uom_id.id == line.product_id.uom_id.id:
                            product_uom = line.product_id.uom_id.id
                            product_qty = line.po_grn_qty
                            price_unit = line.po_line_id.price_subtotal / product_qty
                            
                    if line.billing_type == 'free':
                        
                        if line.uom_id.id != line.product_id.uom_id.id:
                            product_uom = line.product_id.uom_id.id
                            po_coeff = line.product_id.po_uom_coeff
                            product_qty = line.po_grn_qty * po_coeff
                            price_unit =  line.price_subtotal / product_qty
                                
                        elif line.uom_id.id == line.product_id.uom_id.id:
                            product_uom = line.product_id.uom_id.id
                            product_qty = line.po_grn_qty
                            price_unit =  line.price_subtotal / product_qty
                        
                        
                    print "purchase_line_id................",grn_entry.po_id.id
                        
                    stock_move_obj.create(cr,uid,
                        {
                        
                        'po_grn_id':grn_entry.id,
                        'po_grn_line_id':line.id,
                        'purchase_line_id':line.po_line_id.id,
                        'po_id':grn_entry.po_id.id,
                        'product_id': line.product_id.id,
                        'brand_id': line.brand_id.id,
                        'name':line.product_id.name,
                        'product_qty': product_qty,
                        'po_to_stock_qty':product_qty,
                        'stock_uom':product_uom,
                        'product_uom': product_uom,
                        'location_id': grn_entry.supplier_id.property_stock_supplier.id,
                        'location_dest_id': dest_location_id,
                        'move_type': 'in',
                        'state': 'done',
                        'price_unit': price_unit or 0.0,
                        'origin':grn_entry.po_id.name,
                        'stock_rate':price_unit or 0.0,
                        'billing_type':line.billing_type
                        
                        })
                    if grn_entry.grn_dc == 'dc_invoice':    
                        pi_po_grn_obj.create(cr,uid,
                                {
                                
                                'po_grn_id':grn_entry.id,
                                'po_grn_line_id':line.id,
                                'purchase_line_id':line.po_line_id.id,
                                'po_id':line.po_id.id,
                                'product_id': line.product_id.id,
                                'dc_no':grn_entry.dc_no,
                                'po_so_no':line.po_line_id.order_id.name,
                                'po_so_qty': line.po_qty,
                                'tot_rec_qty':line.po_grn_qty,
                                'uom_id':line.uom_id.id,
                                'total_amt': line.po_grn_qty * line.price_unit,
                                'price_unit': line.price_unit or 0.0,
                                'discount': line.kg_discount,
                                'kg_discount_per': line.kg_discount_per,
                                'invoice_tax_ids': [(6, 0, [x.id for x in line.grn_tax_ids])],
                                'net_amt': line.price_subtotal or 0.0,
                                'invoice_header_id' :invoice_no
                                
                                })

                    line.write({'state':'done'})
                    
                    
                if grn_entry.grn_type == 'from_so':
                    
                    if line.billing_type == 'cost':
                
                        if line.uom_id.id != line.product_id.uom_id.id:
                            product_uom = line.product_id.uom_id.id
                            po_coeff = line.product_id.po_uom_coeff
                            product_qty = line.po_grn_qty * po_coeff
                            price_unit =  line.so_line_id.price_subtotal / product_qty
                                
                        elif line.uom_id.id == line.product_id.uom_id.id:
                            product_uom = line.product_id.uom_id.id
                            product_qty = line.po_grn_qty
                            price_unit = line.so_line_id.price_subtotal / product_qty
                            
                    if line.billing_type == 'free':
                        
                        if line.uom_id.id != line.product_id.uom_id.id:
                            product_uom = line.product_id.uom_id.id
                            po_coeff = line.product_id.po_uom_coeff
                            product_qty = line.po_grn_qty * po_coeff
                            price_unit =  line.price_subtotal / product_qty
                                
                        elif line.uom_id.id == line.product_id.uom_id.id:
                            product_uom = line.product_id.uom_id.id
                            product_qty = line.po_grn_qty
                            price_unit =  line.price_subtotal / product_qty
                    
                    if line.si_line_id and line.so_line_id.service_id.gp_id:        
                        sql1 = """ update kg_gate_pass_line set grn_pending_qty=(grn_pending_qty - %s) where si_line_id = %s and gate_id = %s"""%(product_qty,
                                                            line.si_line_id.id,line.so_line_id.service_id.gp_id.id)
                        cr.execute(sql1)
                    elif not line.si_line_id and line.so_line_id.service_id.gp_id:
                        
                        sql1 = """ update kg_gate_pass_line set grn_pending_qty=(grn_pending_qty - %s) where product_id = %s and gate_id = %s"""%(product_qty,
                                                            line.product_id.id,line.so_line_id.service_id.gp_id.id)
                                                            
                                                            
                        cr.execute(sql1)    
                    else:
                        pass    
            
                        
                    stock_move_obj.create(cr,uid,
                        {
                        
                        'po_grn_id':grn_entry.id,
                        'po_grn_line_id':line.id,
                        'so_line_id':line.so_line_id.id,
                        'so_id':grn_entry.so_id.id,
                        'product_id': line.product_id.id,
                        'brand_id': line.brand_id.id,
                        'name':line.product_id.name,
                        'product_qty': product_qty,
                        'po_to_stock_qty':product_qty,
                        'stock_uom':product_uom,
                        'product_uom': product_uom,
                        'location_id': grn_entry.supplier_id.property_stock_supplier.id,
                        'location_dest_id': dest_location_id,
                        'move_type': 'in',
                        'state': 'done',
                        'price_unit': price_unit or 0.0,
                        'origin':grn_entry.so_id.name,
                        'stock_rate':price_unit or 0.0,
                        
                        })
                        
                    if grn_entry.grn_dc == 'dc_invoice':    
                        pi_po_grn_obj.create(cr,uid,
                                {
                                
                                'po_grn_id':grn_entry.id,
                                'po_grn_line_id':line.id,
                                'so_line_id':line.so_line_id.id,
                                'so_id':line.so_line_id.service_id.id,
                                'product_id': line.product_id.id,
                                'dc_no':grn_entry.dc_no,
                                'po_so_no':line.so_line_id.service_id.name,
                                'po_so_qty': line.so_qty,
                                'tot_rec_qty':line.po_grn_qty,
                                'uom_id':line.uom_id.id,
                                'total_amt': line.po_grn_qty * line.price_unit,
                                'price_unit': line.price_unit or 0.0,
                                'discount': line.kg_discount,
                                'kg_discount_per': line.kg_discount_per,
                                'invoice_tax_ids': [(6, 0, [x.id for x in line.grn_tax_ids])],
                                'net_amt': line.price_subtotal or 0.0,
                                'invoice_header_id' :invoice_no
                                
                                })

                    line.write({'state':'done'})
                    
                if grn_entry.grn_type == 'from_gp':
                    
                    
                            
                    if line.billing_type == 'free':
                        
                        if line.uom_id.id != line.product_id.uom_id.id:
                            product_uom = line.product_id.uom_id.id
                            po_coeff = line.product_id.po_uom_coeff
                            product_qty = line.po_grn_qty * po_coeff
                            price_unit =  line.price_subtotal / product_qty
                                
                        elif line.uom_id.id == line.product_id.uom_id.id:
                            product_uom = line.product_id.uom_id.id
                            product_qty = line.po_grn_qty
                            price_unit =  line.price_subtotal / product_qty
                    
                    
                        
                    stock_move_obj.create(cr,uid,
                        {
                        
                        'po_grn_id':grn_entry.id,
                        'po_grn_line_id':line.id,
                        'gp_line_id':line.gp_line_id.id,
                        'gp_id':line.gp_line_id.gate_id.id,
                        'product_id': line.product_id.id,
                        'brand_id': line.brand_id.id,
                        'name':line.product_id.name,
                        'product_qty': product_qty,
                        'po_to_stock_qty':product_qty,
                        'stock_uom':product_uom,
                        'product_uom': product_uom,
                        'location_id': grn_entry.supplier_id.property_stock_supplier.id,
                        'location_dest_id': dest_location_id,
                        'move_type': 'in',
                        'state': 'done',
                        'price_unit': price_unit or 0.0,
                        'origin':line.gp_line_id.gate_id.name,
                        'stock_rate':price_unit or 0.0,
                        
                        })
                        
                    

                    line.write({'state':'done'})
                # This code will create Production lot
                
                # UOM Checking #
                
                if grn_entry.grn_type == 'from_po':
                    
                    if line.po_exp_id:
                        print "sssssssssssssssss"
                        for exp in line.po_exp_id:
                            if line.billing_type == 'cost':
                
                                if line.uom_id.id != line.product_id.uom_id.id:
                                    product_uom = line.product_id.uom_id.id
                                    po_coeff = line.product_id.po_uom_coeff
                                    product_qty = line.po_grn_qty * po_coeff
                                    price_unit =  line.po_line_id.price_subtotal / product_qty
                                        
                                elif line.uom_id.id == line.product_id.uom_id.id:
                                    product_uom = line.product_id.uom_id.id
                                    product_qty = line.po_grn_qty
                                    price_unit = line.po_line_id.price_subtotal / product_qty
                            
                            if line.billing_type == 'free':
                                
                                if line.uom_id.id != line.product_id.uom_id.id:
                                    product_uom = line.product_id.uom_id.id
                                    po_coeff = line.product_id.po_uom_coeff
                                    product_qty = line.po_grn_qty * po_coeff
                                    price_unit =  line.price_subtotal / product_qty
                                        
                                elif line.uom_id.id == line.product_id.uom_id.id:
                                    product_uom = line.product_id.uom_id.id
                                    product_qty = line.po_grn_qty
                                    price_unit =  line.price_subtotal / product_qty
                                    
                            lot_obj.create(cr,uid,
                                    
                                {
                                
                                'grn_no':line.po_grn_id.name,
                                'product_id':line.product_id.id,
                                'brand_id':line.brand_id.id,
                                'product_uom':product_uom,
                                'product_qty':product_qty,
                                'pending_qty':product_qty,
                                'issue_qty':product_qty,
                                'batch_no':exp.batch_no,
                                'expiry_date':exp.exp_date,
                                'price_unit':price_unit or 0.0,
                                'po_uom':line.uom_id.id,
                                'grn_type':'material'
                                
                            })
                                
                    else:
                        if line.billing_type == 'cost':
                
                            if line.uom_id.id != line.product_id.uom_id.id:
                                product_uom = line.product_id.uom_id.id
                                po_coeff = line.product_id.po_uom_coeff
                                product_qty = line.po_grn_qty * po_coeff
                                price_unit =  line.po_line_id.price_subtotal / product_qty
                                    
                            elif line.uom_id.id == line.product_id.uom_id.id:
                                product_uom = line.product_id.uom_id.id
                                product_qty = line.po_grn_qty
                                price_unit = line.po_line_id.price_subtotal / product_qty
                            
                        if line.billing_type == 'free':
                            
                            if line.uom_id.id != line.product_id.uom_id.id:
                                product_uom = line.product_id.uom_id.id
                                po_coeff = line.product_id.po_uom_coeff
                                product_qty = line.po_grn_qty * po_coeff
                                price_unit =  line.price_subtotal / product_qty
                                    
                            elif line.uom_id.id == line.product_id.uom_id.id:
                                product_uom = line.product_id.uom_id.id
                                product_qty = line.po_grn_qty
                                price_unit =  line.price_subtotal / product_qty
                            
                        print "nnnnnnnnnnnnnnnnn"
                        lot_obj.create(cr,uid,
                                    
                            {
                            
                            'grn_no':line.po_grn_id.name,
                            'product_id':line.product_id.id,
                            'brand_id':line.brand_id.id,
                            'product_uom':product_uom,
                            'product_qty':product_qty,
                            'pending_qty':product_qty,
                            'issue_qty':product_qty,
                            'price_unit':price_unit or 0.0,
                            'po_uom':product_uom,
                            'batch_no':line.po_grn_id.name,
                            'grn_type':'material'
                            
                        })
                        
                if grn_entry.grn_type == 'from_so':
                    
                    if line.po_exp_id:
                        print "sssssssssssssssss"
                        for exp in line.po_exp_id:
                            if line.billing_type == 'cost':
                
                                if line.uom_id.id != line.product_id.uom_id.id:
                                    product_uom = line.product_id.uom_id.id
                                    po_coeff = line.product_id.po_uom_coeff
                                    product_qty = line.po_grn_qty * po_coeff
                                    price_unit =  line.so_line_id.price_subtotal / product_qty
                                        
                                elif line.uom_id.id == line.product_id.uom_id.id:
                                    product_uom = line.product_id.uom_id.id
                                    product_qty = line.po_grn_qty
                                    price_unit = line.so_line_id.price_subtotal / product_qty
                            
                            if line.billing_type == 'free':
                                
                                if line.uom_id.id != line.product_id.uom_id.id:
                                    product_uom = line.product_id.uom_id.id
                                    po_coeff = line.product_id.po_uom_coeff
                                    product_qty = line.po_grn_qty * po_coeff
                                    price_unit =  line.price_subtotal / product_qty
                                        
                                elif line.uom_id.id == line.product_id.uom_id.id:
                                    product_uom = line.product_id.uom_id.id
                                    product_qty = line.po_grn_qty
                                    price_unit =  line.price_subtotal / product_qty
                            print "exp................................",exp
                            lot_obj.create(cr,uid,
                                    
                                {
                                
                                'grn_no':line.po_grn_id.name,
                                'product_id':line.product_id.id,
                                'brand_id':line.brand_id.id,
                                'product_uom':product_uom,
                                'product_qty':product_qty,
                                'pending_qty':product_qty,
                                'issue_qty':product_qty,
                                'batch_no':exp.batch_no,
                                'expiry_date':exp.exp_date,
                                'price_unit':price_unit or 0.0,
                                'po_uom':line.uom_id.id,
                                'grn_type':'service'
                                
                            })
                                
                    else:
                        if line.billing_type == 'cost':
                
                            if line.uom_id.id != line.product_id.uom_id.id:
                                product_uom = line.product_id.uom_id.id
                                po_coeff = line.product_id.po_uom_coeff
                                product_qty = line.po_grn_qty * po_coeff
                                price_unit =  line.so_line_id.price_subtotal / product_qty
                                    
                            elif line.uom_id.id == line.product_id.uom_id.id:
                                product_uom = line.product_id.uom_id.id
                                product_qty = line.po_grn_qty
                                price_unit = line.so_line_id.price_subtotal / product_qty
                            
                        if line.billing_type == 'free':
                            
                            if line.uom_id.id != line.product_id.uom_id.id:
                                product_uom = line.product_id.uom_id.id
                                po_coeff = line.product_id.po_uom_coeff
                                product_qty = line.po_grn_qty * po_coeff
                                price_unit =  line.price_subtotal / product_qty
                                    
                            elif line.uom_id.id == line.product_id.uom_id.id:
                                product_uom = line.product_id.uom_id.id
                                product_qty = line.po_grn_qty
                                price_unit =  line.price_subtotal / product_qty
                            
                        print "nnnnnnnnnnnnnnnnn"
                        lot_obj.create(cr,uid,
                                    
                            {
                            
                            'grn_no':line.po_grn_id.name,
                            'product_id':line.product_id.id,
                            'brand_id':line.brand_id.id,
                            'product_uom':product_uom,
                            'product_qty':product_qty,
                            'pending_qty':product_qty,
                            'issue_qty':product_qty,
                            'price_unit':price_unit or 0.0,
                            'po_uom':product_uom,
                            'batch_no':line.po_grn_id.name,
                            'grn_type':'service'
                            
                        })
                
                if grn_entry.grn_type == 'from_gp':
                    
                    if line.po_exp_id:
                        print "sssssssssssssssss"
                        for exp in line.po_exp_id:
                            
                            if line.billing_type == 'free':
                                
                                if line.uom_id.id != line.product_id.uom_id.id:
                                    product_uom = line.product_id.uom_id.id
                                    po_coeff = line.product_id.po_uom_coeff
                                    product_qty = line.po_grn_qty * po_coeff
                                    price_unit =  line.price_subtotal / product_qty
                                        
                                elif line.uom_id.id == line.product_id.uom_id.id:
                                    product_uom = line.product_id.uom_id.id
                                    product_qty = line.po_grn_qty
                                    price_unit =  line.price_subtotal / product_qty
                            print "exp................................",exp
                            lot_obj.create(cr,uid,
                                    
                                {
                                
                                'grn_no':line.po_grn_id.name,
                                'product_id':line.product_id.id,
                                'brand_id':line.brand_id.id,
                                'product_uom':product_uom,
                                'product_qty':product_qty,
                                'pending_qty':product_qty,
                                'issue_qty':product_qty,
                                'batch_no':exp.batch_no,
                                'expiry_date':exp.exp_date,
                                'price_unit':price_unit or 0.0,
                                'po_uom':line.uom_id.id,
                                'grn_type':'service'
                                
                            })
                                
                    else:
                        
                        if line.billing_type == 'free':
                            
                            if line.uom_id.id != line.product_id.uom_id.id:
                                product_uom = line.product_id.uom_id.id
                                po_coeff = line.product_id.po_uom_coeff
                                product_qty = line.po_grn_qty * po_coeff
                                price_unit =  line.price_subtotal / product_qty
                                    
                            elif line.uom_id.id == line.product_id.uom_id.id:
                                product_uom = line.product_id.uom_id.id
                                product_qty = line.po_grn_qty
                                price_unit =  line.price_subtotal / product_qty
                            
                        print "nnnnnnnnnnnnnnnnn"
                        lot_obj.create(cr,uid,
                                    
                            {
                            
                            'grn_no':line.po_grn_id.name,
                            'product_id':line.product_id.id,
                            'brand_id':line.brand_id.id,
                            'product_uom':product_uom,
                            'product_qty':product_qty,
                            'pending_qty':product_qty,
                            'issue_qty':product_qty,
                            'price_unit':price_unit or 0.0,
                            'po_uom':product_uom,
                            'batch_no':line.po_grn_id.name,
                            'grn_type':'service'
                            
                        })
                #Write a tax amount in line
                product_tax_amt = self._amount_line_tax(cr, uid, line, context=context)
                cr.execute("""update po_grn_line set product_tax_amt = %s where id = %s"""%(product_tax_amt,line.id))
                
            self.write(cr,uid,ids[0],{'state':'done',
                                  'approve_flag':'True',
                                  'approved_by':uid,
                                  'approve_date':today })
            cr.execute("""select all_transaction_mails('PO/SO GRN Approval',%s)"""%(ids[0]))
            data = cr.fetchall();
            vals = self.email_ids(cr,uid,ids,context = context)
            if (not vals['email_to']) or (not vals['email_cc']):
                pass
            else:
                ir_mail_server = self.pool.get('ir.mail_server')
                msg = ir_mail_server.build_email(
                        email_from = vals['email_from'][0],
                        email_to = vals['email_to'],
                        subject = " PO/SO GRN - Approved",
                        body = data[0][0],
                        email_cc = vals['email_cc'],
                        object_id = ids[0] and ('%s-%s' % (ids[0], 'kg.po.grn')),
                        subtype = 'html',
                        subtype_alternative = 'plain')
                res = ir_mail_server.send_email(cr, uid, msg,mail_server_id=1, context=context)                     
            if grn_entry.billing_status == 'applicable':
                self.write(cr,uid,ids[0],{'invoice_flag':'True'})
            if grn_entry.grn_type == 'from_so' and grn_entry.so_id.gp_id:
                sql = """ select * from kg_gate_pass_line where grn_pending_qty > 0 and gate_id = %s"""%(grn_entry.so_id.gp_id.id)
                cr.execute(sql)
                data = cr.dictfetchall()
                if data:
                    gate_obj.write(cr,uid,grn_entry.so_id.gp_id.id,{'in_state':'pending'})
                else:
                    gate_obj.write(cr,uid,grn_entry.so_id.gp_id.id,{'in_state':'done'})
            return True
        
    ## GRN to PO Bill creation Part ##
    
    def _get_invoice_type(self, pick):
        print "_get_invoice_type called from PICKING^^^^^^^^^^^^^^^^^^^^66"
        move_obj = self.pool.get('stock.move')
        src_usage = dest_usage = None
        inv_type = None
        if pick.state == 'done':
            move_ids = pick.line_ids
            for move_id in move_ids:
                src_usage = move_id.location_id.usage
                dest_usage = move_id.location_dest_id.usage
                
            if pick.type == 'out' and dest_usage == 'supplier':
                inv_type = 'in_refund'
            elif pick.type == 'out' and dest_usage == 'customer':
                inv_type = 'out_invoice'
            elif pick.type == 'in' and src_usage == 'supplier':
                inv_type = 'in_invoice'
            elif pick.type == 'in' and src_usage == 'customer':
                inv_type = 'out_refund'
            else:
                inv_type = 'in_invoice'
        return inv_type
    
    def action_invoice_create(self, cr, uid, ids, journal_id=False,
            group=False, type='out_invoice', context=None):
                
        print "action_invoice_create =============================FROM KGGGGG>>>"
        
        if context is None:
            context = {}

        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        partner_obj = self.pool.get('res.partner')
        po_obj = self.pool.get('purchase.order')
        pol_obj = self.pool.get('purchase.order.line')
        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')
        
        invoices_group = {}
        res = {}
        inv_type = type
        for picking in self.browse(cr, uid, ids, context=context):
            print "picking ------------------>>>>>", picking
            po_rec = picking.po_id
            print "po_rec __________________________>>>>>", po_rec
            po_obj.write(cr,uid,po_rec.id, {'bill_flag': True})         
            
            partner = picking.supplier_id
            if isinstance(partner, int):
                partner = partner_obj.browse(cr, uid, [partner], context=context)[0]
            if not partner:
                raise osv.except_osv(_('Error, no partner!'),
                    _('Please put a partner on the picking list if you want to generate invoice.'))

            if not inv_type:
                inv_type = self._get_invoice_type(picking)
            print "inv_type ::::::::::::; =====>>>>>>>>........", inv_type
            if group and partner.id in invoices_group:
                invoice_id = invoices_group[partner.id]
                print "invoice_id ---------------------------...........", invoice_id
                invoice = invoice_obj.browse(cr, uid, invoice_id)
                invoice_vals_group = self._prepare_invoice_group(cr, uid, picking, partner, invoice, context=context)
                invoice_obj.write(cr, uid, [invoice_id], invoice_vals_group, context=context)
            else:
                invoice_vals = self._prepare_invoice(cr, uid, picking, partner, inv_type, journal_id, context=context)
                invoice_id = invoice_obj.create(cr, uid, invoice_vals, context=context)
                invoices_group[partner.id] = invoice_id
            res[picking.id] = invoice_id
            move_ids = move_obj.search(cr, uid, [('po_grn_id','=',picking.id),('billing_type','=','cost')])
            print "move_ids.................",move_ids
            for move_id in move_ids:
                move_line = move_obj.browse(cr, uid, move_id)
                if move_line.state == 'cancel':
                    continue
                if move_line.scrapped:
                    # do no invoice scrapped products
                    continue
                    
                vals = self._prepare_invoice_line(cr, uid, group, picking, move_line,
                            invoice_id, invoice_vals, context=context)
                print "vals...........................",vals

                if vals:
                    invoice_line_id = invoice_line_obj.create(cr, uid, vals, context=context)
                    #picking_obj._invoice_line_hook(cr, uid, move_line, invoice_line_id)
                if move_line.purchase_line_id:
                    pl_id = move_line.purchase_line_id.id
                    pol_obj.write(cr, uid, pl_id, {'line_bill': True})                  

            invoice_obj.button_compute(cr, uid, [invoice_id], context=context,
                    set_total=(inv_type in ('in_invoice', 'in_refund')))
            self.write(cr, uid, [picking.id], {
                'state': 'inv',
                }, context=context)
            #picking_obj._invoice_hook(cr, uid, picking, invoice_id)
        self.write(cr, uid, res.keys(), {
            'state': 'inv',
            'invoice_flag': False
            }, context=context)
        return res
    
    def _prepare_invoice(self, cr, uid, picking, partner, inv_type, journal_id, context=None):
        print "_prepare_invoice called from PICKING^^^^^^^^^^^^^^^^^^^^FROM KGGG"
        print "picking =========================>>>>",picking.type
        po_rec = picking.po_id
        print "po_id +++++++++++++++++++++++++>>>>", po_rec
        val1 = po_rec.value1 or 0.0
        val2 = po_rec.value2 or 0.0
        other_ch1 = po_rec.po_expenses_type1 or False
        other_ch2 = po_rec.po_expenses_type2 or False
        sub = po_rec.amount_untaxed
        dis = po_rec.discount
        tax = po_rec.amount_tax
        total = po_rec.amount_total
        other_charge = val1 + val2
        bill = po_rec.bill_type
        if isinstance(partner, int):
            partner = self.pool.get('res.partner').browse(cr, uid, partner, context=context)
        if inv_type in ('out_invoice', 'out_refund'):
            payment_term = partner.property_payment_term.id or False
        else:
            payment_term = partner.property_supplier_payment_term.id or False
        comment = 'Invoice'
        
        invoice_vals = {
        
            'name': self.pool.get('ir.sequence').get(cr, uid, 'account.invoice'),
            'origin': (picking.name or ''),
            'type': inv_type,
            #'account_id': account_id,
            'partner_id': partner.id,
            'comment': comment,
            'payment_term': payment_term,
            'fiscal_position': partner.property_account_position.id,
            'date_invoice': context.get('date_inv', False),
            'company_id': picking.company_id.id,
            'user_id': uid,
            'po_id':picking.po_id.id,
            'grn_id':picking.id,
            'po_expenses_type1':other_ch1,
            'po_expenses_type2':other_ch2,
            'value1':val1,
            'value2':val2,
            'state':'proforma',
            'supplier_invoice_number': context.get('sup_inv_no', False),
            'sup_inv_date': context.get('sup_inv_date', False),
            'bill_type':'credit',
            'po_date':po_rec.date_order,
            'grn_date':picking.grn_date,
            'amount_untaxed':po_rec.amount_untaxed,
            'amount_tax':po_rec.amount_tax,
            'tot_discount':po_rec.discount,
            'other_charge':other_charge
            
            
            
            
        }
        #cur_id = self.get_currency_id(cr, uid, picking)
        #if cur_id:
            #invoice_vals['currency_id'] = cur_id
        if journal_id:
            invoice_vals['journal_id'] = journal_id
        return invoice_vals

    def _prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id,
        invoice_vals, context=None):
        print "_prepare_invoice_line called from PICKING^^^^^^^^^^^^^^^^^^^^FROM KGGG"
        pol_rec = move_line.purchase_line_id
        
        if group:
            name = (picking.name or '') + '-' + move_line.name
        else:
            name = move_line.name
        origin = move_line.po_grn_id.name or ''
        if move_line.po_grn_id.name:
            origin += ':' + move_line.po_grn_id.name

        if invoice_vals['type'] in ('out_invoice', 'out_refund'):
            account_id = move_line.product_id.property_account_income.id
            if not account_id:
                account_id = move_line.product_id.categ_id.\
                        property_account_income_categ.id
        else:
            account_id = move_line.product_id.property_account_expense.id
            if not account_id:
                account_id = move_line.product_id.categ_id.\
                        property_account_expense_categ.id
        if invoice_vals['fiscal_position']:
            fp_obj = self.pool.get('account.fiscal.position')
            fiscal_position = fp_obj.browse(cr, uid, invoice_vals['fiscal_position'], context=context)
            account_id = fp_obj.map_account(cr, uid, fiscal_position, account_id)
        # set UoS if it's a sale and the picking doesn't have one
        uos_id = move_line.product_uom.id
            
        

        return {
            'name': name,
            'origin': origin,
            'invoice_id': invoice_id,
            'uos_id': uos_id,
            'poline_id':move_line.purchase_line_id,
            'product_id': move_line.product_id.id,
            'brand_id': move_line.brand_id.id,
            #'account_id': account_id,
            'price_unit': pol_rec.price_unit,
            'quantity': move_line.product_qty or 0.00,
            'invoice_line_tax_id': [(6, 0, [x.id for x in move_line.po_grn_line_id.grn_tax_ids])],
            #'account_analytic_id': picking_obj._get_account_analytic_invoice(cr, uid, picking, move_line),
            'discount':pol_rec.kg_discount_per,
            'kg_disc_amt':pol_rec.kg_discount,
        }
        
        
        
    def print_grn(self, cr, uid, ids, context=None):        
        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'kg.po.grn', ids[0], 'send_rfq', cr)
        datas = {
                 'model': 'kg.po.grn',
                 'ids': ids,
                 'form': self.read(cr, uid, ids[0], context=context),
        }
        return {'type': 'ir.actions.report.xml', 'report_name': 'grn.print', 'datas': datas, 'nodestroy': True,'name': 'GRN'}       


kg_po_grn()

class po_grn_line(osv.osv):

    _name = "po.grn.line"
    _description = "PO GRN Line"


    def _amount_line(self, cr, uid, ids, prop, arg, context=None):
        cur_obj=self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            amt_to_per = (line.kg_discount / (line.po_grn_qty * line.price_unit or 1.0 )) * 100
            kg_discount_per = line.kg_discount_per
            tot_discount_per = amt_to_per + kg_discount_per
            price = line.price_unit * (1 - (tot_discount_per or 0.0) / 100.0)
            taxes = tax_obj.compute_all(cr, uid, line.grn_tax_ids, price, line.po_grn_qty, line.product_id, line.po_grn_id.supplier_id)
            cur = line.po_grn_id.supplier_id.property_product_pricelist_purchase.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        return res  
        
    _columns = {
        
        'po_grn_date':fields.date('PO GRN Date'),
        'po_grn_id':fields.many2one('kg.po.grn','PO GRN Entry'),
        'name':fields.char('Product'),
        'product_id':fields.many2one('product.product','Product Name',required=True, domain=[('state','=','approved')]),
        'uom_id':fields.many2one('product.uom','UOM',required=True),
        'po_grn_qty':fields.float('Quantity',required=True),
        'po_qty':fields.float('PO Qty'),
        'so_qty':fields.float('SO Qty'),
        'gp_qty':fields.float('GP Qty'),
        'po_pending_qty':fields.float('PO Pending Qty'),
        'so_pending_qty':fields.float('SO Pending Qty'),
        'gp_pending_qty':fields.float('GP Pending Qty'),
        'price_unit':fields.float('Unit Price',required=True),
        'kg_discount_per': fields.float('Discount (%)', digits_compute= dp.get_precision('Discount')),
        'kg_discount': fields.float('Discount Amount'),
        'grn_tax_ids': fields.many2many('account.tax', 'po_grn_tax', 'order_id', 'taxes_id', 'Taxes'),
        'location_id': fields.many2one('stock.location', 'Source Location'),
        'location_dest_id': fields.many2one('stock.location', 'Destination Location'),
        'po_line_id':fields.many2one('purchase.order.line','PO Line'),
        'po_id':fields.many2one('purchase.order','PO NO'),
        'so_line_id':fields.many2one('kg.service.order.line','SO Line'),
        'so_id':fields.many2one('kg.service.order','SO NO'),
        'gp_line_id':fields.many2one('kg.gate.pass.line','GP Line'),
        'gp_id':fields.many2one('kg.gate.pass','GP NO'),
        'pi_line_id':fields.many2one('purchase.requisition.line','PI Line'),
        'si_line_id':fields.many2one('kg.service.indent.line','SI Line'),
        'po_exp_id':fields.one2many('kg.po.exp.batch','po_grn_line_id','Expiry Line'),
        'state': fields.selection([('draft', 'Draft'), ('confirmed', 'Confirmed'),('done', 'Done'), ('cancel', 'Cancelled')], 'Status',readonly=True),
        'remark':fields.text('Remarks'),
        'price_subtotal': fields.function(_amount_line, string='Line Total', digits_compute= dp.get_precision('Account')),
        
        'brand_id':fields.many2one('kg.brand.master','Brand'),
        
        'so_flag':fields.boolean('SO Flag'),
        'po_flag':fields.boolean('PO Flag'),
        'gp_flag':fields.boolean('PO Flag'),
        
        'billing_type': fields.selection([('free', 'Free'), ('cost', 'Cost')], 'Billing Type'),
        'inward_type': fields.many2one('kg.inwardmaster', 'Inward Type'),
        'ser_no':fields.char('Ser No', size=128, readonly=True),
        'serial_no':fields.many2one('stock.production.lot','Serial No',domain="[('product_id','=',product_id)]", readonly=True),  
        
        'order_no': fields.char('Order NO',readonly=True),
        
        'order_date': fields.char('Order Date',readonly=True),
        'product_tax_amt':fields.float('Tax Amount'),  
    }
    
    def onchange_product_id(self, cr, uid, ids, product_id, uom_id,context=None):
            
        value = {'uom_id': ''}
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            value = {'uom_id': prod.uom_id.id}

        return {'value': value}
    
    def onchange_po_grn_qty(self,cr,uid, ids, po_grn_qty ):
        rec = self.browse(cr,uid,ids[0])
        if rec.po_grn_id.so_id.id:
            service_id = self.pool.get('kg.service.order.line').search(cr,uid,[('service_id','=',rec.po_grn_id.so_id.id)])
            service_rec = self.pool.get('kg.service.order.line').browse(cr,uid,service_id[0])
            pending_qty = service_rec.pending_qty
        else:
            purchase_id = self.pool.get('kg.purchase.order.line').search(cr,uid,[('order_id','=',rec.po_grn_id.po_id.id)])
            purchase_rec = self.pool.get('kg.purchase.order.line').browse(cr,uid,purchase_id[0])
            pending_qty = purchase_rec.pending_qty
        if po_grn_qty > pending_qty:
            raise osv.except_osv(
                        _('Please check the Quantity amount'),
                        _('Quantity Should not be greater than PO Quantity!'))
        return True
    
    _defaults = {
    
        'state':'draft',
        'billing_type':'free'
        
        
    }   

po_grn_line()

class kg_po_exp_batch(osv.osv):

    _name = "kg.po.exp.batch"
    _description = "Expiry Date and Batch NO"

    
    _columns = {
        
        'po_grn_line_id':fields.many2one('po.grn.line','PO GRN Entry Line'),
        'exp_date':fields.date('Expiry Date'),
        'batch_no':fields.char('Batch No'),
        'product_qty':fields.float('Product Qty'),
        
        
    }
    _sql_constraints = [
    
        ('batch_no', 'unique(batch_no)', 'S/N must be unique per Item !!'),
    ]   
    
    
kg_po_exp_batch()


class kg_po_stock_move(osv.osv):

    _name = "stock.move"
    _inherit = "stock.move"

    
    _columns = {
        
        'po_grn_line_id':fields.many2one('po.grn.line','PO GRN Entry Line'),
        'po_grn_id':fields.many2one('kg.po.grn','PO GRN Entry'),
        'po_id':fields.many2one('purchase.order','Purchase Order'),
        'so_id':fields.many2one('kg.service.order','Service Order'),
        'so_line_id':fields.many2one('kg.service.order.line','Service Order Line'),
        'billing_type': fields.selection([('free', 'Free'), ('cost', 'Cost')], 'Billing Type'),
        'brand_id':fields.many2one('kg.brand.master','Brand Name'),
        
        
        
    }       
    
kg_po_stock_move()
