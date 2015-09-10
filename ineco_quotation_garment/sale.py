# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 - INECO PARTNERSHIP LIMITE (<http://www.ineco.co.th>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
import re
#import pooler
from openerp.osv import fields, osv
#from tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp import netsvc
from openerp.addons.ineco_report import jasperclient
import os
import unicodedata
import string
from openerp import tools

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

class sale_property(osv.osv):
    _name = 'sale.property'
    _description = 'Property of Sale Line'
    _columns = {
        'name': fields.char('Description',size=64,required=True),
        'active': fields.boolean('Active'),
        'seq': fields.integer('Sequence', required=True),
        'type': fields.selection([('default','Default'),('cross','Cross Tab'),('form1','Form1'),('fabric','Fabrics and Colors')],'Type')
    }
    _defaults = {
        'active': True,
        'seq': 0,
        'type': 'default',
    }
    _sql_constraints = [
        ('name_unique', 'unique (name)', 'Description must be unique !')
    ]
    _order = 'seq'
    
class sale_gender(osv.osv):
    _name = 'sale.gender'
    _description = 'Gender of Sale'
    _columns = {
        'name': fields.char('Description',size=64,required=True),
        'code': fields.char('Code', size=10),
        'name2': fields.char('Other Description',size=64,required=True),
    }
    _sql_constraints = [
        ('name_unique', 'unique (name)', 'Description must be unique !')
    ]    

class sale_color(osv.osv):
    _name = 'sale.color'
    _description = 'Color of Product Sale'
    _columns = {
        'name': fields.char('Description',size=64,required=True),
        'name2': fields.char('Description2',size=64,),
    }
    _sql_constraints = [
        ('name_unique', 'unique (name)', 'Description must be unique !')
    ] 
    _order = 'name'
    
class sale_size(osv.osv):
    _name = 'sale.size'
    _description = 'Size of Product Sale'
    _columns = {
        'name': fields.char('Description',size=64,required=True),
        'seq': fields.integer('Sequence'),
        'code': fields.char('Code',size=10),
    }
    _sql_constraints = [
        ('name_unique', 'unique (name)', 'Description must be unique !')
    ]     
    _order = 'seq'

class sale_style(osv.osv):
    _name = 'sale.style'
    _description = 'Style of Product Sale'
    _columns = {
        'name': fields.char('Description',size=64,required=True)
    }
    _sql_constraints = [
        ('name_unique', 'unique (name)', 'Description must be unique !')
    ] 
    _order = 'name'
    
class sale_line_property(osv.osv):

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    _name = 'sale.line.property'
    _description = 'Property of Sale Line'
    _columns = {
        'name': fields.text('Description', required=True),
        'sequence': fields.integer('Sequence'),
        'property_id': fields.many2one('sale.property', 'Property',  required=True, ondelete='cascade'),
        'sale_line_id': fields.many2one('sale.order.line', 'Order Line', ondelete='cascade'),
        'order_id':fields.related('sale_line_id', 'order_id', 
            string="Order", type='many2one', relation="sale.order", 
            store={
                'sale.line.property': (lambda self, cr, uid, ids, c={}: ids, [], 10),
            }, readonly=True),
        'note': fields.text('Note'),
        'image': fields.binary('Image'),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized photo", type="binary", multi="_get_image",
            store = {
                'sale.line.property': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized photo of the employee. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved. "\
                 "Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Smal-sized photo", type="binary", multi="_get_image",
            store = {
                'sale.line.property': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized photo of the employee. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
        'fabric': fields.boolean('Fabric'),
        'fabric_category_id': fields.many2one('product.category','Fabric Category'),
        'sub_category_id': fields.many2one('product.category','Sub Category'),
        'product_id': fields.many2one('product.product','Fabrics and Colors'),
        'fabric_quantity': fields.related('fabric_category_id','product_onhand', type='float',
                                            string='Fabric Onhand', readonly=True, store=True),
        'subcategory_quantity': fields.related('sub_category_id','product_onhand', type='float',
                                            string='Sub Category Onhand', readonly=True, store=True),
        'product_quantity': fields.related('product_id','qty_available', type='float',
                                            string='Product Onhand', readonly=True, store=True),
    }

    _defaults = {
        'fabric': False,
    }
    #_sql_constraints = [
    #    ('name_property_unique', 'unique (name, property_id, sale_line_id)', 'Description and property must be unique !')
    #]
    _order = 'sale_line_id, sequence'

    def onchange_property_id(self, cr, uid, ids, property_id, context=None):
        if context==None:
            context={}
        res = {
            'sequence': 100,
            'fabric': False,
        }
        bom_obj = self.pool.get('sale.property').browse(cr, uid, property_id)
        if bom_obj:
            res['sequence'] = bom_obj.seq
            res['fabric'] = bom_obj.type == 'fabric'
        return {
            'value': res,
        }

    def onchange_fabric_category_id(self, cr, uid, ids, category_id, context=None):
        return {'value':
                    {'sub_category_id': False,
                     'product_id': False}
                }

    def onchange_subcategory_id(self, cr, uid, ids, subcategory_id, context=None):
        return {'value':
                    {'product_id': False}
                }

    
class sale_line_property_other(osv.osv):
    _name = 'sale.line.property.other'
    _description = "Color, Gender and Sizing Line"
    _columns = {
        'name': fields.text('Description', required=True),
        'seq': fields.integer('Sequence'),
        'color_id': fields.many2one('sale.color', 'Color' ),
        'gender_id': fields.many2one('sale.gender', 'Gender'),
        'size_id': fields.many2one('sale.size', 'Size'),
        'quantity': fields.integer('Quantity', required=True),
        'sale_line_id': fields.many2one('sale.order.line', 'Order Line', ondelete='cascade'),
        'style_id': fields.many2one('sale.style', 'Style'),
        'note': fields.char('Note', size=32, required=True),
    }
    _defaults = {
        'name': '...',
        'note': '-',
    }
#     _sql_constraints = [
#         ('name_property_unique', 'unique (color_id, gender_id, size_id, sale_line_id, style_id)', 'Data must be unique !')
#     ]
    _order = 'color_id, gender_id, size_id'
    
class sale_order_line(osv.osv):
    
    def _get_order_line(self, cr, uid, ids, context=None):
        result = {}
        for data in self.pool.get('sale.order').browse(cr, uid, ids, context=context):
            for line in data.order_line:
                result[line.id] = True
        return result.keys()
    
    _inherit = 'sale.order.line'
    _columns = {
        'name': fields.text('Description', required=True),
        'order_line_property_ids': fields.one2many('sale.line.property', 'sale_line_id', 'Property'),
        'order_line_property_other_ids': fields.one2many('sale.line.property.other', 'sale_line_id', 'Color, Gender and Sizing'),
        'sampling_qty': fields.integer('Sampling Quantity'),
        'garmentorder_date':fields.related('order_id', 'garment_order_date', type='date', 
            store={
                'sale.order.line': (lambda self, cr, uid, ids, c={}: ids, [], 10),
                'sale.order': (_get_order_line, ['garment_order_date'], 10),
            }, string='MO Date'),
        'dateorder':fields.related('order_id', 'date_order', type='date', 
            store={
                'sale.order.line': (lambda self, cr, uid, ids, c={}: ids, [], 10),
                'sale.order': (_get_order_line, ['garment_order_date'], 10),
            }, string='Date Order'),
    }    
    _defaults = {
        'sampling_qty': 0,
    }

#     def create(self, cr, uid, vals, context=None):
#         order_id = vals.get('order_id', False)
#         product_id = vals.get('product_id', False)
#         if order_id and product_id:
#             sql = """
#                 select count(*) as total from sale_order_line sol
#                 join product_product pp on sol.product_id = pp.id
#                 join product_template pt on pp.product_tmpl_id = pt.id
#                 where order_id = %s and pt.type <> 'service'           
#             """
#             cr.execute(sql % order_id)
#             record_count = cr.fetchone()[0] or 0.0
#             product_obj = self.pool.get('product.product').browse(cr, uid, product_id)
#             if record_count >= 1 and product_obj.type in ('consu','product'):
#                 raise osv.except_osv('Product Sale Exceed!', 'Sale line must be 1 product per Sale Order.') 
#         return super(sale_order_line, self).create(cr, uid, vals, context)
    
class sale_order(osv.osv):

    def _get_original_mo(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'garment_order_no_org': False
            }
            sql = """
                    select
                      garment_order_no
                    from sale_order
                    where 
                      name = '%s'
            """ % obj.origin
            cr.execute(sql)             
            data = cr.fetchone()
            if data and data[0]:
                result[obj.id]['garment_order_no_org'] = data[0] or ''
        return result

    def _get_deposit(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'deposit': 0.00,
                'residual': obj.amount_total,
            }
            sql = """
                select coalesce( sum(amount_total), 0.00) from account_invoice
                where journal_id in (2,10,37,39)
                  and saleorder_id = %s
                  and state not in ('draft','cancel')
              """ % obj.id
            cr.execute(sql)             
            data = cr.fetchone()
            if data and data[0]:
                result[obj.id]['deposit'] = data[0] or ''
                result[obj.id]['residual'] = obj.amount_total - (result[obj.id]['deposit'] or 0.00)
        return result

    def _get_order_total(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'order_total': 0.00,
                'order_total_cost': 0.00,
                'order_unit_cost': 0.00,
            }
            sql = """
                select coalesce(round(sum(sol.product_uom_qty)),0)
                from sale_order_line sol
                join product_product pp on pp.id = sol.product_id
                join product_template pt on pt.id = pp.product_tmpl_id
                where order_id = %s
                  and pt.type <> 'service'
                """ % obj.id
            cr.execute(sql)
            data = cr.fetchone()
            if data and data[0]:
                result[obj.id]['order_total'] = data[0] or ''
            unit_cost = 0.0
            order_cost = 0.0
            for cost_line in obj.process_ids:
                unit_cost += cost_line.unit_cost
                order_cost += cost_line.order_cost
            result[obj.id]['order_total_cost'] = order_cost
            result[obj.id]['order_unit_cost'] = unit_cost

        return result

    def _get_commission(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'commission_ready': False
            }
            sql = """
                select 
                   so.id,
                   garment_order_no,
                   amount_untaxed,
                   (select count(*) from account_invoice ai
                    where type = 'out_invoice'
                      and state = 'paid'
                      and garment_order_no = so.garment_order_no) as invoice_count,
                   (select count(*) from account_invoice ai
                    where type = 'out_refund'
                      and state = 'paid'
                      and garment_order_no = so.garment_order_no) as refund_count,
                   (select coalesce(sum(amount_untaxed),0.00) from account_invoice ai
                    where type = 'out_invoice'
                      and state = 'paid'
                      and garment_order_no = so.garment_order_no) as invoice_amount,
                   (select coalesce(sum(amount_untaxed),0.00) from account_invoice ai
                    where type = 'out_refund'
                      and state = 'paid'
                      and garment_order_no = so.garment_order_no) as refund_amount   
                from
                   sale_order so
                where
                  so.state not in ('draft','cancel') and
                  so.id = %s
                  and so.garment_order_no is not null
                  and amount_untaxed - (select coalesce(sum(amount_untaxed),0.00) from account_invoice ai
                    where type = 'out_refund'
                      and garment_order_no = so.garment_order_no) <= (select coalesce(sum(amount_untaxed),0.00) from account_invoice ai
                    where type = 'out_invoice'
                      and garment_order_no = so.garment_order_no)
              """ % obj.id
            cr.execute(sql)             
            data = cr.fetchone()
            if data and data[0]:
                result[obj.id]['commission_ready'] = data[2] - data[6] <= data[5]
        return result

    def _get_customer_po(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'customer_po_ready': False
            }
            #2015-09-10
            if obj.customer_po_attach or obj.shop_id.skip_customer_po:
                result[obj.id]['customer_po_ready'] = True
        return result

    def _get_residual(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'residual': 0.00
            }
            sql = """
                select coalesce( sum(case when type = 'out_invoice' then amount_total else -amount_total end), 0.00) from account_invoice
                where 
                  type in ('out_invoice','out_refund')
                  and state not in ('draft','cancel')
                  and saleorder_id = %s    
              """ % obj.id
            cr.execute(sql)             
            data = cr.fetchone()
            if data and data[0]:
                result[obj.id]['residual'] = data[0] or ''
        return result

    def _get_pattern(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'date_pattern_finish': False,
                'date_mark_finish': False,
                'pattern_employee': False,
                'sampling_marker': False,
                'sampling_marker_start': False,
                'sampling_marker_finish': False,
                'marker': False,
                'sampling_employee1': False,
                'sampling_employee1_start': False,
                'sampling_employee1_finish': False,
                'sampling_employee2': False,
                'sampling_employee2_start': False,
                'sampling_employee2_finish': False,
            }
            pattern_ids = self.pool.get('ineco.pattern').search(cr, uid, [('saleorder_id','=',obj.id)])
            if pattern_ids:
                pattern = self.pool.get('ineco.pattern').browse(cr, uid, pattern_ids)[0]
                result[obj.id]['date_pattern_finish'] = pattern.date_finish_planned or False
                result[obj.id]['date_mark_finish'] = pattern.date_mark_finish or False
                result[obj.id]['employee_id'] = pattern.employee_id and pattern.employee_id.id or False
                result[obj.id]['marker'] = pattern.marker or False
                result[obj.id]['sampling_marker'] = pattern.sampling_marker or False
                result[obj.id]['sampling_marker_start'] = pattern.sampling_date_mark_start or False
                result[obj.id]['sampling_marker_finish'] = pattern.sampling_date_mark_finish or False
                result[obj.id]['sampling_employee1'] = pattern.sampling_process1_employee or False
                result[obj.id]['sampling_employee1_start'] = pattern.sampling_date_process1_start or False
                result[obj.id]['sampling_employee1_finish'] = pattern.sampling_date_process1_finish or False
                result[obj.id]['sampling_employee2'] = pattern.sampling_process2_employee or False
                result[obj.id]['sampling_employee2_start'] = pattern.sampling_date_process2_start or False
                result[obj.id]['sampling_employee2_finish'] = pattern.sampling_date_process2_finish or False
        return result

    def _get_invoice_paid(self, cr, uid, ids, context=None):
        result = {}
        for data in self.pool.get('account.invoice').browse(cr, uid, ids, context=context):
            result[data.saleorder_id.id] = True
        return result.keys()

    def _get_start_production(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'start_production': False
            }
            #   select count(*) from mrp_production_workcenter_line mpwl
            #    join mrp_production mp on mp.id = mpwl.production_id
            #    where
            #      workcenter_id = 3
            #      and mpwl.state = 'done'
            #      and mp.sale_order_id = %s
            sql = """
                select count(*) from mrp_production
                where sale_order_id = %s and (is_print = True or state not in ('draft','cancel'))
                """ % obj.id
            cr.execute(sql)
            data = cr.fetchone()
            if data and data[0] > 0:
                result[obj.id]['start_production'] = True
        return result

    def _get_production(self, cr, uid, ids, context=None):
        result = {}
        for data in self.pool.get('mrp.production').browse(cr, uid, ids, context=context):
            result[data.sale_order_id.id] = True
        return result.keys()

    _inherit = 'sale.order'
    _description = 'Add Delivery Date'
    _columns = {
        'date_delivery': fields.date('Delivery Date', track_visibility='onchange'),
        'sale_revision': fields.char('Revision', size=32, track_visibility='onchange'),
        'sample_order_no': fields.char('Sampling Order No', size=32, readonly=True, track_visibility='onchange'),
        'garment_order_no': fields.char('Garment Order No', size=32, readonly=True, track_visibility='onchange'),
        'sample_order_date': fields.date('Sampling Order Date', track_visibility='onchange'),
        'garment_order_date': fields.date('Garment Order Date', track_visibility='onchange'),
        'last_garment_order_update': fields.datetime('Last Garment Order Update'),
        'sample_deliver_date': fields.date('Sampling Deliver Date', track_visibility='onchange'),
        'cancel_sample_order': fields.boolean('Cancel Sampling Order', track_visibility='onchange'),
        'cancel_garment_order': fields.boolean('Cancel Garment Order', track_visibility='onchange'),
        'date_sale_close': fields.date('Closed Date', track_visibility='onchange'),
        'sample_revision_no': fields.char('Sampling Revision No', size=32, track_visibility='onchange'),
        'sample_revision_date': fields.date('Sampling Revision Date',track_visibility='onchange'),
        'to_correct': fields.boolean('To Corrected', track_visibility='onchange'),
        'relate_garment_order_no': fields.char('Relate MO', size=32),
        'date_pattern_finish': fields.function(_get_pattern,  string="Pattern Finish", 
                                               type="datetime", multi="_get_pattern"),
        'date_mark_finish': fields.function(_get_pattern,  string="Mark Finish", 
                                               type="datetime", multi="_get_pattern"),
        'employee_id': fields.function(_get_pattern,  string="Employee", 
                                               type="many2one", relation="hr.employee", multi="_get_pattern"),
        'marker': fields.function(_get_pattern,  string="Marker", type="char", multi="_get_pattern"),
        'sampling_marker': fields.function(_get_pattern,  string="Sampling Marker", type="char", multi="_get_pattern"),
        'sampling_marker_start': fields.function(_get_pattern,  string="Start", 
                                               type="datetime", multi="_get_pattern"),
        'sampling_marker_finish': fields.function(_get_pattern,  string="Finish", 
                                               type="datetime", multi="_get_pattern"),
        'sampling_employee1': fields.function(_get_pattern,  string="Cut Employee", type="char", multi="_get_pattern"),
        'sampling_employee1_start': fields.function(_get_pattern,  string="Start", 
                                               type="datetime", multi="_get_pattern"),
        'sampling_employee1_finish': fields.function(_get_pattern,  string="Finish", 
                                               type="datetime", multi="_get_pattern"),
        'sampling_employee2': fields.function(_get_pattern,  string="Sew Employee", type="char", multi="_get_pattern"),
        'sampling_employee2_start': fields.function(_get_pattern,  string="Start", 
                                               type="datetime", multi="_get_pattern"),
        'sampling_employee2_finish': fields.function(_get_pattern,  string="Finish", 
                                               type="datetime", multi="_get_pattern"),
        'pattern_ids': fields.one2many('ineco.pattern','saleorder_id','Patterns'),
        'manager_user_id': fields.many2one('hr.employee','Approval',),
        'garment_order_no_org': fields.function(_get_original_mo, string="Master MO", type="char", multi="_mo"),
        'deposit': fields.function(_get_deposit, string="Deposit", type="float", digits=(12,2), multi="_deposit"),
        'residual': fields.function(_get_deposit, string="Residual", type="float", digits=(12,2), multi="_deposit"),
        'commission_ready': fields.function(_get_commission, string="Commission Ready", 
                    store={
                        'sale.order': (lambda self, cr, uid, ids, c={}: ids, [], 10),
                        'account.invoice': (_get_invoice_paid, ['state'], 10),
                    },
                    type="boolean", multi="_commission"),
        #In-line
        'process_ids': fields.one2many('ineco.sale.order.process','sale_order_id','Processes'),
        'bom_ids': fields.one2many('ineco.sale.order.bom','sale_order_id','Boms'),
        'order_total': fields.function(_get_order_total, string="Order Total", type="integer", multi="_ordertotal"),
        'order_total_cost': fields.function(_get_order_total, string="Order Total Cost", type="float", digits=(12,2), multi="_ordertotal"),
        'order_unit_cost': fields.function(_get_order_total, string="Dozen Cost", type="float", digits=(12,2), multi="_ordertotal"),
        'date_pin_start': fields.date('Date Pin Start'),
        'date_pin_finish': fields.date('Date Pin Finish'),
        'pin_note': fields.text('Pin Note'),
        #2015-06-18
        'start_production': fields.function(_get_start_production, string="Production Ready",
                    store={
                        'sale.order': (lambda self, cr, uid, ids, c={}: ids, [], 10),
                        'mrp.production': (_get_production, ['worker','is_print'], 10),
                    },
                    type="boolean", multi="_production"),
        'nas_ok': fields.boolean('Nas Ready'),
        'customer_po_attach': fields.binary('PO Attachment', ),
        'customer_po_fname': fields.char('File name', size=64,),
        'customer_po_ready': fields.function(_get_customer_po, string="Po Ready",
                    store={
                        'sale.order': (lambda self, cr, uid, ids, c={}: ids, [], 10),
                    },
                    type="boolean", multi="_customer_po"),
        #2015-09-08
        'allow_confirm_sale': fields.boolean('Allow Confirm Sale', track_visibility='onchange'),
        'check_confirm_sale': fields.related('shop_id','allow_confirm_sale',string='Check Confirm Sale',
                                             type='boolean', reaodnly=True),
    }
    _defaults = {
        'cancel_sample_order': False,
        'cancel_garment_order': False,
        'to_correct': False,
        'relate_garment_order_no': False,
        'commission_ready': False,
        'nas_ok': False,
        'customer_po_ready': False,
        'allow_confirm_sale': False,
    }

    def name_get(self, cr, uid, ids, context=None):
        if not isinstance(ids, list) :
            ids = [ids]
        res = []
        if not ids:
            return res
        reads = self.read(cr, uid, ids, ['name', 'garment_order_no'], context)

        for record in reads:
            name = record['name']
            if record['garment_order_no']:
                name = name + '/' + record['garment_order_no']
            res.append((record['id'], name))
        return res

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name:
            ids = self.search(cr, user, [('name','=',name)]+ args, limit=limit, context=context)
            if not ids:
                ids = self.search(cr, user, [('garment_order_no',operator,name)]+ args, limit=limit, context=context)
            if not ids:
                ids = set()
                ids.update(self.search(cr, user, args + [('name',operator,name)], limit=limit, context=context))
                if not limit or len(ids) < limit:
                    ids.update(self.search(cr, user, args + [('name',operator,name)], limit=(limit and (limit-len(ids)) or False) , context=context))
                ids = list(ids)
            if not ids:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    ids = self.search(cr, user, [('name','=', res.group(2))] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}       
        res = super(sale_order, self).write(cr, uid, ids, vals, context=context)
        if vals.get('date_sale_close', False):
            sale_obj = self.pool.get('sale.order').browse(cr, uid, ids)[0]
            if sale_obj.lead_id:
                sale_obj.lead_id.write({'date_closed': sale_obj.date_sale_close,
                                        'date_deadline': sale_obj.date_sale_close })
        return res

    def schedule_generate_pdf(self, cr, uid, ids, context=None):

        validFilenameChars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        def removeDisallowedFilenameChars(filename):
            cleanedFilename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore')
            return ''.join(c for c in cleanedFilename if c in validFilenameChars)

        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        user_print_name = user_obj.name
        report_xml = self.pool.get('ir.actions.report.xml').browse(cr, uid, 533) #Sale Order (Mixprint)
        field_in = report_xml.criteria_field
        url = report_xml.jasper_url
        user = report_xml.jasper_username
        password = report_xml.jasper_password
        report_path = report_xml.jasper_report_path
        parameter = report_xml.parameter_name
        format = 'pdf'
        export_ids = self.search(cr, uid, [('nas_ok','=',False),('garment_order_no','!=',False),('garment_order_date','!=',False)])

        for data in self.browse(cr, uid, export_ids):
            if os.path.exists('/Users/Tititab/pdf'):
                default_path = '/Users/Tititab/pdf'
            else:
                default_path = '/media/mixprint/openerp'
            print default_path
            report_param = {}
            default_path = default_path + '/%s' % (cr.dbname)
            if not os.path.exists(default_path):
                os.makedirs(default_path)
            if data.garment_order_date:
                garment_date = datetime.strptime(data.garment_order_date,'%Y-%m-%d')
                default_path = default_path + '/%s' % (garment_date.year)
                if not os.path.exists(default_path):
                    os.makedirs(default_path)
                default_path = default_path + '/%s' % (garment_date.month)
                if not os.path.exists(default_path):
                    os.makedirs(default_path)
                default_path = default_path + '/%s' % (data.garment_order_no[:2])
                if not os.path.exists(default_path):
                    os.makedirs(default_path)
                if field_in and url and user and password and report_path:
                    criteries = field_in + ' in '+ str(tuple( sorted( [data.id] )))
                    criteries = criteries.replace(',)',')')
                    if parameter:
                        report_param[parameter] = criteries
                        report_param['user_print_name'] = user_print_name
                    j = jasperclient.JasperClient(url,user,password)
                    a = j.runReport(report_path,format, report_param) # {'pick_ids': criteries})
                    if data.partner_id.parent_id:
                        filename = default_path+'/%s-%s.pdf' % (data.garment_order_no,data.partner_id.parent_id.name)
                        #filename = filename
                        try:
                            file = open(filename,'w')
                        except:
                            filename = default_path+'/%s.pdf' % (data.garment_order_no)
                            file = open(filename,'w')
                            pass
                    else:
                        filename = default_path+'/%s-%s.pdf' % (data.garment_order_no,data.partner_id.name)
                        try:
                            file = open(filename,'w')
                        except:
                            filename = default_path+'/%s.pdf' % (data.garment_order_no)
                            file = open(filename,'w')
                            pass
                    file.write(a['data'])
                    data.write({'nas_ok':True})

        return True

    def action_regen_mo(self, cr, uid, ids, context=None):
        self.cancel_mo(cr, uid, ids, context=context)
        self.create_mo(cr, uid, ids, context=context)
        return True

    def action_button_confirm(self, cr, uid, ids, context=None):
        for id in ids:
            sale_obj = self.browse(cr, uid, id)
            if sale_obj.garment_order_no:
                self.create_mo(cr, uid, ids, context)
            if sale_obj.lead_id:
                if sale_obj.lead_id.state == 'cancel':
                    sql = """
                        update crm_lead
                        set probability = 100, state = 'done', stage_id = 6
                        where id = %s
                    """ % (sale_obj.lead_id.id)
                    cr.execute(sql)
                else:
                    sale_obj.lead_id.case_mark_won()
                if sale_obj.date_sale_close:
                    sale_obj.lead_id.write({'date_closed': sale_obj.date_sale_close,
                                            'date_deadline': sale_obj.date_sale_close})
        super(sale_order, self).action_button_confirm(cr, uid, ids, context=context)
        return True

    def action_button_cancelsp(self, cr, uid, ids, context=None):
        for id in ids:
            sale_obj = self.browse(cr, uid, id)
            if sale_obj.sample_order_no:
                pattern_ids = self.pool.get('ineco.pattern').search(cr,uid, [('saleorder_id','=',sale_obj.id)])
                for pattern in self.pool.get('ineco.pattern').browse(cr, uid, pattern_ids):
                    pattern.write({'name': pattern.name+'#CN', 'is_cancel': True})
                sale_obj.write({'cancel_sample_order': True})
        return True
    
    def cancel_mo(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            sale_obj = self.browse(cr, uid, ids)[0]
            production_obj = self.pool.get('mrp.production')
            production_ids = production_obj.search(cr, uid, [('origin','=',sale_obj.name)])
            for prod_id in production_ids:
                prod_name = production_obj.browse(cr, uid, prod_id).name
                production_obj.write(cr, uid, prod_id, {'name': prod_name+'#CN'+time.strftime('%Y-%m-%d %H:%M:%S') })
                wf_service.trg_validate(uid, 'mrp.production', prod_id, 'button_cancel', cr) 
        return True
    
    def create_pattern(self, cr, uid, ids, context=None):
        pattern = self.pool.get('ineco.pattern')
        for id in ids:
            sale_obj = self.browse(cr, uid, [id])[0]
            #Protect Cancel SO -> Duplicate
            sale_ids = self.pool.get('sale.order').search(cr, uid ,[('garment_order_no','=', sale_obj.garment_order_no),('garment_order_no','!=',False)])
            data_ids = pattern.search(cr, uid, [('saleorder_id','=',sale_ids)])
            #data_ids = pattern.search(cr, uid, [('saleorder_id','=',sale_obj.id)])
            other_ids = pattern.search(cr, uid, ['|',('name','=',sale_obj.sample_order_no),('name','=',sale_obj.garment_order_no)])
            if not data_ids:
                if not other_ids:
                    new_pattern_data = {
                        'name': sale_obj.garment_order_no or sale_obj.sample_order_no ,
                        'product_id': 3802, #Product ID as Pattern
                        'saleorder_id': sale_obj.id,
                        'date_start': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'date_expected': time.strftime('%Y-%m-%d  %H:%M:%S'), #sale_obj.sample_deliver_date or time.strftime('%Y-%m-%d'),
                    }
                    new_pattern_id = pattern.create(cr, uid, new_pattern_data)
            else:
                if other_ids:
                    pattern.write(cr, uid, data_ids, {'date_finish': False, 
                                                      'name': sale_obj.garment_order_no or sale_obj.sample_order_no,
                                                      'date_start_planned': False,
                                                      'date_finish_planned': False,
                                                      'is_cancel': False,
                                                      'state': 'draft',
                                                      'saleorder_id': sale_obj.id,
                                                      'date_start': time.strftime('%Y-%m-%d %H:%M:%S'),
                                                      'date_expected': sale_obj.date_delivery}) #sale_obj.date_delivery})
                else:
                    pattern.write(cr, uid, data_ids, {'date_finish': False, 
                                                      'date_start_planned': False,
                                                      'date_finish_planned': False,
                                                      'is_cancel': False,
                                                      'state': 'draft',
                                                      'saleorder_id': sale_obj.id,
                                                      'date_start': time.strftime('%Y-%m-%d %H:%M:%S'),
                                                      'date_expected': sale_obj.date_delivery}) #sale_obj.date_delivery})
        return True
            
    def create_mo(self, cr, uid, ids, context=None):
        self.create_pattern(cr, uid, ids, context)
        for id in ids:
            sale_obj = self.browse(cr, uid, [id])[0]
            production_obj = self.pool.get('mrp.production')
            garment_order_no = sale_obj.garment_order_no 
            company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
            production_obj = self.pool.get('mrp.production')
            wf_service = netsvc.LocalService("workflow")
            bom_obj = self.pool.get('mrp.bom')
            stock_location_obj = self.pool.get('stock.warehouse').browse(cr, uid, [1])[0]
            seq = 1
            for line in sale_obj.order_line:
                bom_id = False
                bom_ids = bom_obj.search(cr, uid, [('product_id','=',line.product_id.id)])
                if bom_ids:
                    bom_id = bom_ids[0]      
                if line.order_line_property_other_ids:
                    for other in line.order_line_property_other_ids:
                        production_obj.create(cr, uid, {
                            'origin': line.order_id.name,
                            'product_id': line.product_id.id,
                            'product_qty': other.quantity,
                            'product_uom': line.product_uom.id,
                            'product_uos_qty': other.quantity,
                            'product_uos': line.product_uom.id,
                            'location_src_id': stock_location_obj.lot_stock_id.id,
                            'location_dest_id': stock_location_obj.lot_stock_id.id,
                            'bom_id': bom_id,
                            'date_planned': line.order_id.date_delivery, #time.strftime('%Y-%m-%d'),
                            'move_prod_id': False,
                            'company_id': line.order_id.company_id.id,
                            'name': garment_order_no+('#%s' % seq),
                            'color_id': other.color_id and other.color_id.id or False,
                            'gender_id': other.gender_id and other.gender_id.id or False,
                            'size_id': other.size_id and other.size_id.id or False,
                            'note': other.note or False,
                            'sale_order_id': line.order_id.id,
                        })  
                        seq += 1      
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        super(sale_order, self).action_cancel(cr, uid, ids, context=context)
        wf_service = netsvc.LocalService("workflow")
        if context is None:
            context = {}
        sale_obj = self.browse(cr, uid, ids)[0]
        if sale_obj.lead_id:
            sale_obj.lead_id.case_mark_lost()

        production_obj = self.pool.get('mrp.production')
        production_ids = production_obj.search(cr, uid, [('origin','=',sale_obj.name)])
        for prod_id in production_ids:
            prod_name = production_obj.browse(cr, uid, prod_id).name
            production_obj.write(cr, uid, prod_id, {'name': prod_name+'#CN'+time.strftime('%Y-%m-%d %H:%M:%S') })
            wf_service.trg_validate(uid, 'mrp.production', prod_id, 'button_cancel', cr) 
        return True

    def copy(self, cr, uid, ids, default=None, context=None):
        if context is None:
            context = {}
        if default is None:
            default = {}
        default = default.copy()
        default['pattern_ids'] = []
        if 'change_shop' in context:
            default['sale_revision'] = False
            default['sample_order_no'] = False
            default['garment_order_no'] = False
            default['sample_order_date'] = False
            default['garment_order_date'] = False
            default['sample_deliver_date'] = False
            default['cancel_sample_order'] = False
            default['cancel_garment_order'] = False
            default['date_sale_close'] = False
            default['sample_revision_no'] = False
            default['sample_revision_date'] = False
            default['date_delivery'] = False
            default['date_order'] = time.strftime('%Y-%m-%d')
        new_id = super(sale_order, self).copy(cr, uid, ids, default, context=context)
        #print 'Duplicate ',ids
        sql = "update ineco_pattern set saleorder_id = %s where saleorder_id = %s" % (new_id, ids)
        cr.execute(sql)
        return new_id
    
    def action_gen_sampling_no(self, cr, uid, ids, context=None):
        sample_order_no = self.pool.get('ir.sequence').get(cr, uid, 'ineco.sampling.order')
        self.write(cr, uid, ids, {'sample_order_no': sample_order_no, 'sample_order_date': time.strftime('%Y-%m-%d'), 'sample_revision_date': time.strftime('%Y-%m-%d')})
        self.create_pattern(cr, uid, ids, context)
        return True

    def action_gen_garment_no(self, cr, uid, ids, context=None):
        sale_obj = self.browse(cr, uid, ids)[0]
        production_obj = self.pool.get('mrp.production')
        production_ids = production_obj.search(cr, uid, [('origin','=',sale_obj.name)])
        garment_order_no = False
        for line in sale_obj.order_line:
            if not line.order_line_property_other_ids:
                raise osv.except_osv('Color-Gender-Size is empty!', 'Please fill in Color/Gender/Size.')             
        if production_ids:
            garment_order = production_obj.browse(cr, uid, production_ids)[0]
            garment_order_no = garment_order.name.split('#')[0]
            self.write(cr, uid, ids, {'garment_order_no': garment_order_no, 'garment_order_date': time.strftime('%Y-%m-%d'),
                                      'last_garment_order_update': time.strftime('%Y-%m-%d %H:%M:%S')})
        else:
            try:
                if sale_obj.shop_id and sale_obj.shop_id.production_sequence_id:
                    garment_order_no = self.pool.get('ir.sequence').get_id(cr, uid, sequence_code_or_id=sale_obj.shop_id.production_sequence_id.id )
                else:
                    garment_order_no = self.pool.get('ir.sequence').get(cr, uid, 'ineco.garment.order')
                self.write(cr, uid, ids, {'garment_order_no': garment_order_no, 'garment_order_date': time.strftime('%Y-%m-%d'),
                                          'last_garment_order_update': time.strftime('%Y-%m-%d %H:%M:%S')})
                self.create_mo(cr, uid, ids, context)
            except:
                cr.rollback()
                raise osv.except_osv('MO ERROR!', 'Generate MO ERROR.')
        return True

    def _prepare_order_picking(self, cr, uid, order, context=None):
        result = super(sale_order, self)._prepare_order_picking(cr, uid, order, context=context)
        result.update({'invoice_state':'2binvoiced', 'delivery_type_id': order.ineco_delivery_type_id.id or False})
        return result
    
    def _prepare_order_line_move_qty(self, cr, uid, order, line, picking_id, date_planned, new_qty, color, gender, size, note=None, context=None):
        location_id = order.shop_id.warehouse_id.lot_stock_id.id
        output_id = order.shop_id.warehouse_id.lot_output_id.id
        return {
            'name': line.name,
            'picking_id': picking_id,
            'product_id': line.product_id.id,
            'date': date_planned,
            'date_expected': date_planned,
            'product_qty': new_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': new_qty,
            'product_uos': (line.product_uos and line.product_uos.id)\
                    or line.product_uom.id,
            'product_packaging': line.product_packaging.id,
            'partner_id': line.address_allotment_id.id or order.partner_shipping_id.id,
            'location_id': location_id,
            'location_dest_id': output_id,
            'sale_line_id': line.id,
            'tracking_id': False,
            'state': 'draft',
            #'state': 'waiting',
            'company_id': order.company_id.id,
            'price_unit': line.product_id.standard_price or 0.0,
            'size_id': size,
            'color_id': color,
            'gender_id': gender,
            'note': note,
        }

    def _get_date_planned(self, cr, uid, order, line, start_date, context=None):
        #date_planned = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=line.delay or 0.0)
        #date_planned = (date_planned - timedelta(days=order.company_id.security_lead)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        date_planned = order.date_delivery
        return date_planned

    def _create_pickings_and_procurements(self, cr, uid, order, order_lines, picking_id=False, context=None):

        sql = """
            select count(*) as total from sale_order_line sol
            join product_product pp on sol.product_id = pp.id
            join product_template pt on pp.product_tmpl_id = pt.id
            where order_id = %s and pt.type <> 'service'           
        """
        cr.execute(sql % order.id)
        record_count = cr.fetchone()[0] or 0.0
        if record_count > 1 :
            raise osv.except_osv('Product Sale Exceed!', 'Sale line must be 1 product per Sale Order.') 
        
        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking.out')
        procurement_obj = self.pool.get('procurement.order')
        production_obj = self.pool.get('mrp.production')
        bom_obj = self.pool.get('mrp.bom')
        proc_ids = []

        for line in order_lines:
            #Check when sale line quantity <> production order qty (other tab)
            if len(line.order_line_property_other_ids) > 0:
                other_qty = 0
                for other in line.order_line_property_other_ids:
                    other_qty = other_qty + other.quantity
                if other_qty <> line.product_uom_qty:
                    raise osv.except_osv('Invalid Quantity!', 'Sale line quantity <> production.')
                
            if line.state == 'done':
                continue

            date_planned = self._get_date_planned(cr, uid, order, line, order.date_order, context=context)

            if line.product_id:
                if line.product_id.type in ('product', 'consu'):
                    stock_location_obj = self.pool.get('stock.warehouse').browse(cr, uid, [1])[0]
                    bom_id = False
                    bom_ids = bom_obj.search(cr, uid, [('product_id','=',line.product_id.id)])
                    if bom_ids:
                        bom_id = bom_ids[0]
                    if not picking_id:
                        picking_id = picking_obj.create(cr, uid, self._prepare_order_picking(cr, uid, order, context=context))
                    if line.order_line_property_other_ids:
                        seq = 0
                        for other in line.order_line_property_other_ids:
                            seq += 1
                            move_id = move_obj.create(cr, uid, self._prepare_order_line_move_qty(cr, 
                                uid, order, line, picking_id, date_planned, other.quantity, 
                                other.color_id and other.color_id.id or False,
                                other.gender_id and other.gender_id.id or False,
                                other.size_id and other.size_id.id or False, other.note or False, context=context))
                    else:
                        move_id = move_obj.create(cr, uid, self._prepare_order_line_move(cr, uid, order, line, picking_id, date_planned, context=context))
                else:
                    # a service has no stock move
                    move_id = False

                proc_id = procurement_obj.create(cr, uid, self._prepare_order_line_procurement(cr, uid, order, line, move_id, date_planned, context=context))
                proc_ids.append(proc_id)
                line.write({'procurement_id': proc_id})
                self.ship_recreate(cr, uid, order, line, move_id, proc_id)

        wf_service = netsvc.LocalService("workflow")
        if picking_id:
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
        for proc_id in proc_ids:
            wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)

        val = {}
        if order.state == 'shipping_except':
            val['state'] = 'progress'
            val['shipped'] = False

            if (order.order_policy == 'manual'):
                for line in order.order_line:
                    if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                        val['state'] = 'manual'
                        break
        order.write(val)
        return True

class crm_lead(osv.osv):
    _inherit = 'crm.lead'
    _description = "Cost of CRM on Opportunity"
    _columns = {
        'cost_ids': fields.one2many('ineco.crm.cost','lead_id', 'Costs'),
    }

class ineco_crm_cost(osv.osv):

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = line.quantity * line.cost
            res[line.id] = price
        return res

    def on_change_costtype(self, cr, uid, ids, cost_type_id, context=None):
        if context==None:
            context={}
        result = 0.0
        cost_type_obj = self.pool.get('ineco.cost.type').browse(cr, uid, cost_type_id)
        if cost_type_obj:
            result = cost_type_obj.cost
        return {'value': {
            'cost': result,
            }
        }

    _name = 'ineco.crm.cost'
    _description = "Cost of CRM Line"
    _columns = {
        'name': fields.char('Description', size=128),
        'lead_id': fields.many2one('crm.lead', 'Opportunity'),
        'cost_type_id': fields.many2one('ineco.cost.type','Cost'),
        'quantity': fields.integer('Quantity', required=True),
        'cost': fields.float('Cost', required=True),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
    }
    
    _defaults = {
        'quantity': 1,
        'cost': 0.0,
    }

class ineco_sale_order_bom(osv.osv):
    _name = 'ineco.sale.order.bom'
    _description = "Sale Order Bom"
    _columns = {
        'name': fields.char('Description', size=254),
        'sale_order_id': fields.many2one('sale.order','Sale Order'),
        'process_bom_id': fields.many2one('ineco.mrp.process.bom','BOM Process'),
        'process_ids': fields.one2many('ineco.sale.order.process','sale_bom_id','Process'),
        #2015-06-23
        'date_pin_start': fields.datetime('Pin Start'),
        'date_pin_finish': fields.datetime('Pin Finish'),
        'process_total': fields.integer('Process Total'),
        'pin_count': fields.integer('Pin Count'),
        'workcenter_id': fields.many2one('mrp.workcenter', 'Workcenter',),
        'machine_id': fields.many2one('ineco.mrp.machine', 'Machine',),
    }

    def onchange_bom_id(self, cr, uid, ids, bom_id, context=None):
        if context==None:
            context={}
        result = '...'
        bom_obj = self.pool.get('ineco.mrp.process.bom').browse(cr, uid, bom_id)
        if bom_obj:
            result = bom_obj.name
        return {'value': {
            'name': result,
            }
        }

    def button_load_process(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        line_obj = self.pool.get('ineco.sale.order.process')
        for data in self.browse(cr, uid, ids):
            if data.process_bom_id:
                for process in data.process_bom_id.line_ids:
                    new_data = {
                        'sale_bom_id': data.id,
                        'process_id': process.process_id.id,
                        'name': process.name,
                        'sequence': process.sequence,
                        'unit_cost': process.process_id.cost,
                    }

                    line_obj.create(cr, uid, new_data)
        return True


class ineco_sale_order_process(osv.osv):

    def _get_cost(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            order_total = 0.0
            if obj.sale_order_id:
                sql = """
                    select coalesce(round(sum(sol.product_uom_qty)),0)
                    from sale_order_line sol
                    join product_product pp on pp.id = sol.product_id
                    join product_template pt on pt.id = pp.product_tmpl_id
                    where order_id = %s
                      and pt.type <> 'service'
                    """ % obj.sale_order_id.id
                cr.execute(sql)
                data = cr.fetchone()
                if data and data[0]:
                    order_total = data[0] or 0.0
            result[obj.id] = {
                'order_total': 0.0,
                'order_total_dozen': 0.0,
                'order_cost': 0.0,
            }
            result[obj.id]['order_total'] = order_total
            result[obj.id]['order_total_dozen'] = (order_total / 12) or 0.0
            result[obj.id]['order_cost'] = ((order_total / 12) or 0.0) * obj.unit_cost
        return result

    _name = 'ineco.sale.order.process'
    _description = "Sale Process"
    _columns = {
        'name': fields.char('Description', size=128),
        #'sale_order_id': fields.many2one('sale.order','Sale Order'),
        'sale_bom_id': fields.many2one('ineco.sale.order.bom','BOM'),
        'sale_order_id':fields.related('sale_bom_id', 'sale_order_id', string="Sale Order", type='many2one', relation="sale.order",
            store={
                'ineco.sale.order.process': (lambda self, cr, uid, ids, c={}: ids, [], 10),
            }, readonly=True),
        'sequence': fields.integer('Sequence'),
        'process_id': fields.many2one('ineco.mrp.process','Process'),
        'unit_cost': fields.float('Unit Cost'),
        'order_total': fields.function(_get_cost, string="Order Total", type="integer", multi="_cost"),
        'process_cost':fields.related('process_id', 'cost', string="Dozen Cost", type='float', readonly=True),
        'order_total_dozen': fields.function(_get_cost, string="Order Dozen", type="float", digits=(12,2), multi="_cost"),
        'order_cost': fields.function(_get_cost, string="Total", type="float", digits=(12,2), multi="_cost"),
    }
    _defaults = {
        'sequence': 10,
    }
    _order = 'sale_order_id, sale_bom_id, sequence'

    def onchange_process_id(self, cr, uid, ids, process_id, context=None):
        if context==None:
            context={}
        result = 0.0
        cost_type_obj = self.pool.get('ineco.mrp.process').browse(cr, uid, process_id)
        if cost_type_obj:
            result = cost_type_obj.cost or 0.0
        return {'value': {
            'unit_cost': result,
            }
        }

#2015-09-08
class sale_shop(osv.osv):
    _inherit = "sale.shop"
    _description = "Add Auto Sequence, Stock Journal"
    _columns = {
        'allow_confirm_sale': fields.boolean('Allow Confirm Sale'),
        #2015-09-10
        'skip_customer_po': fields.boolean('Skip Customer PO'),
    }
    _defaults = {
        'allow_confirm_sale': False,
        'skip_customer_po': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: