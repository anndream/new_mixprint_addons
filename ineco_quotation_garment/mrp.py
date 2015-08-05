# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

#import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv
#from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
#from openerp.tools import float_compare
#from openerp.tools.translate import _
from openerp import netsvc
from openerp import tools

class ineco_mrp_pattern_component(osv.osv):
    _name = 'ineco.mrp.pattern.component'
    _description = "Pattern Component"
    _columns = {
        'name': fields.char('Description', size=64,),
        'seq': fields.integer('Sequence'),
        'type_id': fields.many2one('ineco.pattern.type','Type',required=True),
        'process1': fields.boolean('Process 1'),
        'process2': fields.boolean('Process 2'),
        'production_id': fields.many2one('mrp.production','Production'),
    }
    _defaults = {
        'name': '...',
        'process1': False,
        'process2': False,
        #'last_updated': time.strftime("%Y-%m-%d %H:%M:%S"),
    }

class mrp_production(osv.osv):

    def _get_late(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        today = datetime.now()
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'late': True
            }
            if obj.date_plan_start and not obj.date_plan_finish :
                start_date = datetime.strptime(obj.date_plan_start, '%Y-%m-%d %H:%M:%S') + relativedelta(days=3)
                if today > start_date:
                    result[obj.id]['late'] = True
                else:
                    result[obj.id]['late'] = False
         
        return result

    def _get_datefinish(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'date_plan_finish2': obj.date_plan_finish or False
            }
        return result
    
    _inherit = 'mrp.production'
    _description = 'MRP for Garment'
    _columns = {
        'date_plan_start': fields.datetime('Date Plan Start'),
        'date_plan_finish': fields.datetime('Date Plan Finish'),
        'color_id': fields.many2one('sale.color', 'Color'),
        'gender_id': fields.many2one('sale.gender', 'Gender'),
        'size_id': fields.many2one('sale.size', 'Size'),        
        'note': fields.char('Note', size=32,),
        'sale_order_id': fields.many2one('sale.order','Sale Order',select=True),
        'pattern_id': fields.many2one('ineco.pattern','Pattern'),
        'comment': fields.text('Comment'),
        'bill_no': fields.char('Bill No', size=10),
        'bill_type': fields.char('Material Type', size=64),
        'worker': fields.char('Worker',size=64),
        'bill_weight': fields.float('Bill Weight'),
        'pattern_component_ids': fields.one2many('ineco.mrp.pattern.component','production_id','Components'),
        'is_print': fields.boolean('Print MO'),
        'late': fields.function(_get_late, string="Late", type="boolean", multi="_late"),
        'user_id': fields.related('sale_order_id', 'user_id', type='many2one', relation="res.users", string='Sale', readonly=True),
        'is_planning': fields.boolean('Print Planning'),
        'date_plan_finish2': fields.function(_get_datefinish, string="Cut Finish", type="date", multi="_finish",
            store = {
                'mrp.production': (lambda self, cr, uid, ids, c={}: ids, [], 10),
            },),
        'date_process1_start': fields.datetime('Date Collar Start'),
        'date_process1_finish': fields.datetime('Date Collar Finish'),
        'partner_id': fields.related('sale_order_id','partner_id',type="many2one",relation="res.partner",string="Customer"),
        'ticket_ids': fields.one2many('ineco.mrp.production.ticket','production_id','Tickets'),
        'ticket_size': fields.integer('Ticket Size'),
        'machine_id': fields.many2one('ineco.mrp.machine', 'Machine'),
    }
    _defaults = {
        'is_print': False,
        'is_planning': False,
        'ticket_size': 100,
    }

    def button_done_draft(self, cr, uid, ids, *args):
        if not len(ids):
            return False
        wf_service = netsvc.LocalService("workflow")
        for doc_id in ids:
            cr.execute("select id from wkf where osv = '"+'mrp.production'+"'")
            wkf_ids = map(lambda x: x[0], cr.fetchall())
            wkf_id = wkf_ids[0]
            cr.execute("select id from wkf_activity where wkf_id = %s and name = 'draft'" % (wkf_id))
            act_ids = map(lambda x: x[0], cr.fetchall())
            act_id = act_ids[0]
            cr.execute('update wkf_instance set state=%s where res_id=%s and res_type=%s', ('active', doc_id, 'mrp.production'))
            cr.execute("update wkf_workitem set state = 'active', act_id = %s where inst_id = (select id from wkf_instance where wkf_id = %s and res_id = %s)", (str(act_id), str(wkf_id), doc_id))    
            self.write(cr, uid, doc_id, {'state':'draft'})
        return True    

    def button_component(self, cr, uid, ids, context=None):
        for id in ids:
            production = self.browse(cr, uid, id)
            if production and production.pattern_id:
                sql = "delete from ineco_mrp_pattern_component where production_id = %s" % production.id
                cr.execute(sql)
                sql = "delete from ineco_mrp_production_ticket where production_id = %s and pattern_id = %s" % (production.id, production.pattern_id.id)
                cr.execute(sql)
                pattern_obj = self.pool.get('ineco.pattern')
                pattern_ids = pattern_obj.search(cr, uid, [('saleorder_id','=',production.sale_order_id.id),('saleorder_id','!=',False)])
                for pattern in pattern_obj.browse(cr, uid, pattern_ids):                    
                    #for component in production.pattern_id.component_ids:
                    for component in pattern.component_ids:
                        new_data = {
                            'seq': component.seq,
                            'type_id': component.type_id.id,
                            'production_id': production.id,
                        }
                        self.pool.get('ineco.mrp.pattern.component').create(cr, uid, new_data)
                full_ticket = 0
                ticket_obj = self.pool.get('ineco.mrp.production.ticket')
                #while full_ticket <  production.product_qty // production.ticket_size:
                #    ticket_new = {
                #        'name': production.name + (production.gender_id and production.gender_id.name)+'#'+ \
                #            (production.color_id and production.color_id.name)+'#'+ \
                #            (production.size_id and production.size_id.name)+ ('-T%s' % (full_ticket+1)),
                #        'production_id': production.id,
                #        'pattern_id': production.pattern_id.id,
                #        'quantity': production.ticket_size,
                #    }
                #    ticket_obj.create(cr, uid, ticket_new)
                #    full_ticket += 1
                if production.product_qty > 0:
                    ticket_new = {
                        'name': production.name + '#'+(production.gender_id and production.gender_id.name)+'#'+ \
                            (production.color_id and production.color_id.name)+'#'+ \
                            (production.size_id and production.size_id.name) ,
                        'quantity': production.product_qty,
                        'pattern_id': production.pattern_id.id,
                        'production_id': production.id,
                    }
                    ticket_obj.create(cr, uid, ticket_new)
                
        return True

    def action_compute(self, cr, uid, ids, properties=None, context=None):
        """ Computes bills of material of a product.
        @param properties: List containing dictionaries of properties.
        @return: No. of products.
        """
        if properties is None:
            properties = []
        results = []
        bom_obj = self.pool.get('mrp.bom')
        uom_obj = self.pool.get('product.uom')
        prod_line_obj = self.pool.get('mrp.production.product.line')
        workcenter_line_obj = self.pool.get('mrp.production.workcenter.line')
        for production in self.browse(cr, uid, ids):
            cr.execute('delete from mrp_production_product_line where production_id=%s', (production.id,))
            cr.execute('delete from mrp_production_workcenter_line where production_id=%s', (production.id,))
            bom_point = production.bom_id
            bom_id = production.bom_id.id
            if not bom_point:
                bom_id = bom_obj._bom_find(cr, uid, production.product_id.id, production.product_uom.id, properties)
                if bom_id:
                    bom_point = bom_obj.browse(cr, uid, bom_id)
                    routing_id = bom_point.routing_id.id or False
                    self.write(cr, uid, [production.id], {'bom_id': bom_id, 'routing_id': routing_id})

            if not bom_id:
                raise osv.except_osv(_('Error!'), _("Cannot find a bill of material for this product."))
            factor = uom_obj._compute_qty(cr, uid, production.product_uom.id, production.product_qty, bom_point.product_uom.id)
            res = bom_obj._bom_explode(cr, uid, bom_point, factor / bom_point.product_qty, properties, routing_id=production.routing_id.id)
            results = res[0]
            results2 = res[1]
            for line in results:
                line['production_id'] = production.id
                prod_line_obj.create(cr, uid, line)
            pattern_ids = self.pool.get('ineco.pattern').search(cr, uid, [('saleorder_id','=',production.sale_order_id.id)])
            pattern_obj = False
            if pattern_ids:
                pattern_obj =  self.pool.get('ineco.pattern').browse(cr, uid, pattern_ids)[0]
            for line in results2:
                if pattern_obj:
                    if line['multiple_component']:
                        line['cycle'] = (int(line['cycle']) or 1.0) * len(pattern_obj.component_ids) or 1.0
                line['production_id'] = production.id
                line['name'] = line['name'] +' : '+production.name
                workcenter_line_obj.create(cr, uid, line)
        return len(results)
 
    
class mrp_routing_workcenter(osv.osv):
    """
    Defines working cycles and hours of a Work Center using routings.
    """
    _inherit = 'mrp.routing.workcenter'
    _columns = {
        'multiple_component': fields.boolean('Multiple Pattern Component'),
    }
    _default = {
        'multiple_component': False,
    }
    
class mrp_production_workcenter_line(osv.osv):

    def _get_datefinish(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'date_finished2': obj.date_finished or False
            }
        return result
    
    _inherit = 'mrp.production.workcenter.line'
    _columns = {
        'multiple_component': fields.boolean('Multiple Pattern Component'),
#        'cycle_count': fields.float('Cycle Counts', digits=(16,2)),
        'size_id': fields.related('production_id', 'size_id', type='many2one', relation='sale.size', string='Size', readonly=True),
        'note': fields.related('production_id', 'note', type='char', string='Note', size=100, readonly=True),
        'worker': fields.related('production_id', 'worker', type='char', string='Worker', readonly=True),
        'date_finished2': fields.function(_get_datefinish, string="Date Finish", type="date", multi="_finish",
            store = {
                'mrp.production.workcenter.line': (lambda self, cr, uid, ids, c={}: ids, [], 10),
            },),
    }
    _default = {
#        'cycle_count': 0.0,
        'multiple_component': False,
    }

def rounding(f, r):
    import math
    if not r:
        return f
    return math.ceil(f / r) * r

class mrp_bom(osv.osv):
    _inherit = 'mrp.bom'
    def _bom_explode(self, cr, uid, bom, factor, properties=None, addthis=False, level=0, routing_id=False):
        """ Finds Products and Work Centers for related BoM for manufacturing order.
        @param bom: BoM of particular product.
        @param factor: Factor of product UoM.
        @param properties: A List of properties Ids.
        @param addthis: If BoM found then True else False.
        @param level: Depth level to find BoM lines starts from 10.
        @return: result: List of dictionaries containing product details.
                 result2: List of dictionaries containing Work Center details.
        """
        routing_obj = self.pool.get('mrp.routing')
        factor = factor / (bom.product_efficiency or 1.0)
        factor = rounding(factor, bom.product_rounding)
        if factor < bom.product_rounding:
            factor = bom.product_rounding
        result = []
        result2 = []
        phantom = False
        if bom.type == 'phantom' and not bom.bom_lines:
            newbom = self._bom_find(cr, uid, bom.product_id.id, bom.product_uom.id, properties)

            if newbom:
                res = self._bom_explode(cr, uid, self.browse(cr, uid, [newbom])[0], factor*bom.product_qty, properties, addthis=True, level=level+10)
                result = result + res[0]
                result2 = result2 + res[1]
                phantom = True
            else:
                phantom = False
        if not phantom:
            if addthis and not bom.bom_lines:
                result.append(
                {
                    'name': bom.product_id.name,
                    'product_id': bom.product_id.id,
                    'product_qty': bom.product_qty * factor,
                    'product_uom': bom.product_uom.id,
                    'product_uos_qty': bom.product_uos and bom.product_uos_qty * factor or False,
                    'product_uos': bom.product_uos and bom.product_uos.id or False,
                })
            routing = (routing_id and routing_obj.browse(cr, uid, routing_id)) or bom.routing_id or False
            if routing:
                for wc_use in routing.workcenter_lines:
                    wc = wc_use.workcenter_id
                    d, m = divmod(factor, wc_use.workcenter_id.capacity_per_cycle)
                    mult = (d + (m and 1.0 or 0.0))
                    cycle = mult * wc_use.cycle_nbr
                    result2.append({
                        'name': tools.ustr(wc_use.name) + ' - '  + tools.ustr(bom.product_id.name),
                        'workcenter_id': wc.id,
                        'sequence': level+(wc_use.sequence or 0),
                        'cycle': cycle,
                        'hour': float(wc_use.hour_nbr*mult + ((wc.time_start or 0.0)+(wc.time_stop or 0.0)+cycle*(wc.time_cycle or 0.0)) * (wc.time_efficiency or 1.0)),
                        'multiple_component': wc_use.multiple_component or False,
                    })
            for bom2 in bom.bom_lines:
                res = self._bom_explode(cr, uid, bom2, factor, properties, addthis=True, level=level+10)
                result = result + res[0]
                result2 = result2 + res[1]
        return result, result2
    
    
class ineco_mrp_production_ticket(osv.osv):
    _name = 'ineco.mrp.production.ticket'
    _description = 'Production Tickets'
    _columns = {
        'name': fields.char('Code', size=64),
        'quantity': fields.integer('Quantity'),
        'production_id': fields.many2one('mrp.production','Production'),
        'pattern_id': fields.many2one('ineco.pattern','Pattern'),
        'machine_id': fields.many2one('ineco.mrp.machine','Machine'),
        'gender_id': fields.related('production_id', 'gender_id', type='many2one', relation="sale.gender", string='Gender', readonly=True),
        'color_id': fields.related('production_id', 'color_id', type='many2one', relation="sale.color", string='Color', readonly=True),
        'size_id': fields.related('production_id', 'size_id', type='many2one', relation="sale.size", string='Size', store=True, readonly=True),
        'size_seq': fields.related('size_id', 'seq', type='integer', string='Size Seq', store=True, readonly=True),
        'note': fields.related('production_id', 'note', type='char', size=64, string='Note', store=True, readonly=True),
    }
    _order = 'machine_id, size_seq, production_id'

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            encode = name.split(':')
            if len(encode) == 3:
                ids = self.search(cr, user, [('id','=',encode[0])] + args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('name',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    def button_split(self, cr, uid, ids, *args):
        return True
    
class ineco_mrp_machine(osv.osv):
    _name = 'ineco.mrp.machine'
    _description = 'Machine'
    _columns = {
        'name': fields.char('Machine Code', size=128, required=True),
        'code': fields.char('Machine Serial', size=32),
        'seq': fields.integer('Sequence', ),
        'brand': fields.char('Brand', size=128,),
        'model': fields.char('Model', size=128,),
        'type': fields.char('Type', size=128,),
        'workcenter_id': fields.many2one('mrp.workcenter', 'Workcenter',),
        'active': fields.boolean('Active'),
    }
    
    _defaults = {
        'active': True,
    }
    
    _sql_constraints = [
        ('name_unique',
         'unique (name)',
         'Machine name must be unique.')
    ]

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('code','=',name)] + args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('name',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    
class ineco_mrp_process_group(osv.osv):
    _name = 'ineco.mrp.process.group'
    _description = "Process Group"
    _columns = {
        'name': fields.char('Process Group Name', size=64, required=True),
    }
    _sql_constraints = [
        ('name_unique',
         'unique (name)',
         'Process Group Name must be unique.')
    ]
    
class ineco_mrp_process(osv.osv):
    _name = 'ineco.mrp.process'
    _inherit = ['mail.thread']
    _description = "MRP Process"
    _columns = {
        'code': fields.char('Barcode', size=32, required=True, track_visibility='onchange'),
        'name': fields.char('Process Name', size=64, required=True, track_visibility='onchange'),
        'process_group_id': fields.many2one('ineco.mrp.process.group','Group',),
        'cost': fields.float('Costing', digits=(12,2),required=True, track_visibility='onchange'),
        'level': fields.selection([('begin','Beginner'),('medium','Medium'),('hard','Hard')],'Level'),
        'image_multi': fields.text('Image List'),
        'attachments': fields.one2many('ir.attachment', 'mrp_process_id', string="Attachments"),
    }
    _defaults = {
        'cost': 1.0,
    }
    _sql_constraints = [
        ('name_group_unique',
         'unique (name, process_group_id)',
         'Process Name and Group must be unique.')
    ]

    def name_get(self, cr, uid, ids, context=None):
        if not isinstance(ids, list) :
            ids = [ids]
        res = []
        if not ids:
            return res
        reads = self.read(cr, uid, ids, ['id', 'name', 'cost'], context)

        for record in reads:
            name = record['name']
            if record['cost']:
                name = name + ' (' + ('%0.2f' % record['cost'] or 0.0)+')'
            res.append((record['id'], name))
        return res

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('code','=',name)] + args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('name',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)
    
    
class ineco_mrp_period(osv.osv):
    _name = 'ineco.mrp.period'
    _descrition = "MRP Period"
    _columns = {
        'name': fields.char('Period Name', size=32, required=True),
        'seq': fields.integer('Sequence', required=True),
        'time_start': fields.float('Start Time', required=True),
        'time_stop': fields.float('Stop Time', required=True),
        #'hours': fields.float('Hours', required=True),
        'code': fields.char('Barcode',size=32,required=True),
        'active': fields.boolean('Active'),
    }
    _defaults = {
        'active': True,
        #'hours': 1.0,
        'seq': 1,
    }
    _order = 'seq'

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('code','=',name)] + args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('name',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

class ineco_mrp_task_list(osv.osv):
    _name = 'ineco.mrp.task.list'
    _inherit = ['mail.thread']
    _description = 'Task List'
    _columns = {
        'name': fields.char('Description',size=64,),
        'employee_id': fields.many2one('hr.employee','Employee',required=True, track_visibility='onchange'),
        'date': fields.date('Task Date', required=True, track_visibility='onchange'),
        'machine_id': fields.many2one('ineco.mrp.machine','Machine', required=True, track_visibility='onchange'),
        'task_ids': fields.one2many('ineco.mrp.task','list_id','Tasks'),
    }
    _defaults = {
        'name': '...'
    }
    _order = 'date,employee_id'
    
class ineco_mrp_task(osv.osv):
    _name = 'ineco.mrp.task'
    _description = "MRP Task"
    _columns = {
        'name': fields.char('Description',size=64,),
        'list_id': fields.many2one('ineco.mrp.task.list','Task List',ondelete="cascade"),
        'employee_id': fields.many2one('hr.employee','Employee',required=True),
        'date': fields.date('Task Date', required=True),
        'period_id': fields.many2one('ineco.mrp.period','Period', required=True),
        'machine_id': fields.many2one('ineco.mrp.machine','Machine', required=True),
        'ticket_barcode': fields.char('Ticket',size=64,require=True),
        'process_id': fields.many2one('ineco.mrp.process','Process',required=True),
        'ticket_id': fields.many2one('ineco.mrp.production.ticket','Ticket', ),
        'production_id': fields.many2one('mrp.production','Production'),
        'pattern_type_id': fields.many2one('ineco.pattern.type','Pattern Type',),
        'good': fields.integer('Good'),
        'no_good': fields.integer('No Good'),
    }
    _defaults = {
        'date': time.strftime('%Y-%m-%d'),
    }

    def create(self, cr, uid, data, context=None):
        data['date'] = time.strftime('%Y-%m-%d')
        result = super(ineco_mrp_task, self).create(cr, uid, data, context=context)
        #self.post_write(cr, uid, [result], context=context)
        return result

    def onchange_ticket_id(self, cr, uid, ids, ticket_id=False, context=None):
        res = {}
        if ticket_id:
            ticket = self.pool.get('ineco.mrp.production.ticket').browse(cr, uid, ticket_id)
            
            res['value'] = {'production_id': ticket.production_id.id,
                            'pattern_type_id': False}
        return res

    def onchange_ticket_barcode(self, cr, uid, ids, ticket=False, context=None):
        res = {}
        if ticket:
            encode = ticket.split(':')
            if len(encode) == 3:
                ticket = self.pool.get('ineco.mrp.production.ticket').browse(cr, uid, int(encode[0]))
                pattern_type = self.pool.get('ineco.pattern.type').browse(cr, uid, int(encode[2]))
                res['value'] = {'production_id': ticket.production_id.id,
                                'ticket_id': ticket.id,
                                'pattern_type_id': pattern_type.id}
        return res    
    
class ineco_mrp_subworkcenter(osv.osv):
    _name = 'ineco.mrp.subworkcenter'
    _description = "Sub Workcenter"
    _columns = {
        'name': fields.char('Sub Workcenter', size=128, required=True),
        'workcenter_id': fields.many2one('mrp.workcenter', 'Workcenter', required=True)
    }
    
class ineco_mrp_subworkcenter_task(osv.osv):

    def _get_product(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'product_id': False
            }
            if obj.saleorder_id :
                for line in obj.saleorder_id.order_line:
                    if result[obj.id]['product_id'] == False:
                        result[obj.id]['product_id'] = line.product_id.id         
        return result

    def _get_day(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'day_month': False
            }
            if obj.date:          
                result[obj.id]['day_month'] = "%02d" % time.strptime(obj.date,'%Y-%m-%d').tm_mday         
        return result
    
    _name = 'ineco.mrp.subworkcenter.task'
    _description = 'Sub Workcenter Task'
    _columns = {
        'name': fields.char('Description', size=128),
        'subworkcenter_id': fields.many2one('ineco.mrp.subworkcenter', 'Sub Workcenter', required=True),
        'date': fields.date('Date Done', required=True),
        'saleorder_id': fields.many2one('sale.order', 'Sale Order'),
        'garment_order_no': fields.related('saleorder_id', 'garment_order_no', string='Garment Order No', type='char', store=True),
        'garment_order_date': fields.related('saleorder_id', 'garment_order_date', string='Garment Order Date', type='date'),
        'date_delivery': fields.related('saleorder_id', 'date_delivery', string='Delivery Date',type='date'),
        'customer_id': fields.related('saleorder_id', 'partner_id', string='Customer',type='many2one', relation='res.partner', store=True),
        'product_id': fields.function(_get_product, string="Product", type="many2one", multi="_product", relation="product.product", store=True),
        #'product_id': fields.related('saleorder_id', 'product_id', string="Product",type='many2one',relation='product.product'),
        #'quantity_order': fields.related('saleorder_id', string="Order Qty",type='integer'),
        'quantity': fields.integer('Quantity'),
        'user_id': fields.related('saleorder_id','user_id',string="Sale",type='many2one',relation='res.users',store=True),
        'day_month': fields.function(_get_day, string="Day", type="char", size=2, multi="_day", 
                store={
                    'ineco.mrp.subworkcenter.task': (lambda self, cr, uid, ids, c={}: ids, [], 10),
                }),
        'type': fields.selection([('out','Out'),('in','In')],'Type')
    }
    _defaults = {
        'date': fields.date.context_today ,
        'type': 'out',
    }
    _order = 'date'
    
    def create(self, cr, uid, data, context=None):
        if not 'date' in data:
            data['date'] = time.strftime('%Y-%m-%d')
        result = super(ineco_mrp_subworkcenter_task, self).create(cr, uid, data, context=context)
        return result

class ineco_mrp_tag(osv.osv):

    def _get_quantity(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            total = 0.0
            amount = 0.0
            for line in obj.line_ids:
                total += line.quantity
            for process in obj.tag_process_ids:
                amount += process.cost * (total / 12.0)
            result[obj.id] = {
                'totals': total,
                'amount': amount,
            }
        return result

    def _get_day(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'day_month': False
            }
            if obj.start_datetime:
                result[obj.id]['day_month'] = "%02d" % time.strptime(obj.start_datetime,'%Y-%m-%d %H:%M:%S').tm_mday
        return result

    _name = 'ineco.mrp.tag'
    _inherit = ['mail.thread']
    _description = "MRP Tag"
    _columns = {
        'name': fields.char('Tag No', size=32, required=True),
        'sale_order_id': fields.many2one('sale.order','Sale Order', track_visibility='onchange'),
        'garment_order_no': fields.related('sale_order_id','garment_order_no', type="char", string="Garment No",
                store={
                    'ineco.mrp.tag': (lambda self, cr, uid, ids, c={}: ids, [], 10),
                }, readonly=True),
        'customer_id': fields.related('sale_order_id','partner_id',type="many2one", relation="res.partner",
                store={
                    'ineco.mrp.tag': (lambda self, cr, uid, ids, c={}: ids, [], 10),
                },
            string="Customer", readonly=True),
        'user_id': fields.related('sale_order_id','user_id',type="many2one", relation="res.users", string="Sale Person",
            readonly=True),
        'sequence': fields.integer('Sequence'),
        'totals': fields.function(_get_quantity, string="Activity Total", type="integer", multi="_quantity", track_visibility='onchange',
            store = {
                'ineco.mrp.tag': (lambda self, cr, uid, ids, c={}: ids, [], 10),
            },),
        'amount': fields.function(_get_quantity, string="Amount", type="float", digits=(12,2), multi="_quantity", track_visibility='onchange',
            store = {
                'ineco.mrp.tag': (lambda self, cr, uid, ids, c={}: ids, [], 10),
            },),
        'date': fields.date('Date', track_visibility='onchange'),
        'start_datetime': fields.datetime('Start Date', track_visibility='onchange'),
        'finish_datetime': fields.datetime('Finish Date', track_visibility='onchange'),
        'employee_id': fields.many2one('hr.employee','Employee', track_visibility='onchange'),
        'line_ids': fields.one2many('ineco.mrp.tag.line','mrp_tag_id','Tag Items'),
        'tag_process_ids': fields.many2many('ineco.mrp.process', 'ineco_tag_process_rel', 'child_id', 'parent_id', 'Process'),
        'state': fields.selection([('draft','Draft'),('done','Done'),('cancel','Cancel')],'State',readonly=True, track_visibility='onchange'),
        'day_month': fields.function(_get_day, string="Day", type="char", size=2, multi="_day",
                store={
                    'ineco.mrp.tag': (lambda self, cr, uid, ids, c={}: ids, [], 10),
                }),
        'coach_id': fields.related('employee_id','coach_id',type="many2one", relation="hr.employee", string="Coach",
                store={
                    'ineco.mrp.tag': (lambda self, cr, uid, ids, c={}: ids, [], 10),
                }, readonly=True),
    }

    _defaults = {
        'name': '/',
        'sequence': 1.0,
        'date': lambda self, cr, uid, ctx: fields.date.context_today(self, cr, uid, ctx),
        'state': 'draft',
    }

    def create(self, cr, uid, vals, context=None):
        if vals.get('name','/')=='/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'ineco.mrp.tag') or '/'
        return super(ineco_mrp_tag, self).create(cr, uid, vals, context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if context is None:
            context = {}
        default = default.copy()
        default['line_ids'] = []
        default['employee_id'] = False
        default['start_datetime'] = False
        default['finish_datetime'] = False
        default['name'] = self.pool.get('ir.sequence').get(cr, uid, 'ineco.mrp.tag')
        return super(ineco_mrp_tag, self).copy(cr, uid, id, default, context=context)

    def button_load(self, cr, uid, ids, context=None):
        obj_packing_line = self.pool.get('ineco.mrp.tag.line')
        for data in self.browse(cr, uid, ids):
            for line in data.sale_order_id.order_line:
                for property in line.order_line_property_other_ids:
                    new_data = {
                        'sale_line_property_other_id': property.id,
                        'mrp_tag_id': data.id,
                        'product_id': line.product_id.id,
                    }
                    find_ids = obj_packing_line.search(cr, uid, [('mrp_tag_id','=', data.id),('sale_line_property_other_id','=',property.id)])
                    if not find_ids:
                        obj_packing_line.create(cr, uid, new_data)
        return True

    def button_reset(self, cr, uid, ids, context=None):
        obj_packing_line = self.pool.get('ineco.mrp.tag.line')
        for data in self.browse(cr, uid, ids):
            line_ids = obj_packing_line.search(cr, uid, [('mrp_tag_id','=',data.id),('quantity','=',False)])
            if line_ids:
                obj_packing_line.unlink(cr, uid, line_ids)
        return True


class ineco_mrp_tag_line(osv.osv):
    _name = 'ineco.mrp.tag.line'
    _description = "MRP Tag Line"
    _columns = {
        'name': fields.char('Description', size=32),
        'mrp_tag_id': fields.many2one('ineco.mrp.tag','Tag'),
        'sale_line_property_other_id': fields.many2one('sale.line.property.other','Property Other'),
        'product_id': fields.many2one('product.product','Product', readonly=True),
        'color_id': fields.related('sale_line_property_other_id', 'color_id', type="many2one", relation='sale.color', string='Color',readonly=True),
        'gender_id': fields.related('sale_line_property_other_id', 'gender_id', type="many2one", relation='sale.gender', string='Gender',readonly=True),
        'size_id': fields.related('sale_line_property_other_id', 'size_id', type="many2one", relation='sale.size', string='Size',readonly=True),
        'note': fields.related('sale_line_property_other_id','note', type="char", string="Note", readonly=True),
        'product_qty': fields.related('sale_line_property_other_id', 'quantity', type="float",  string='Origin Qty',readonly=True),
        'quantity': fields.integer('Quantity'),
    }
    _defaults = {
        'quantity': 0.0,
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if context is None:
            context = {}
        default = default.copy()
        default['quantity'] = 0.0
        return super(ineco_mrp_tag_line, self).copy(cr, uid, id, default, context=context)

class ineco_mrp_process_bom(osv.osv):
    _name = 'ineco.mrp.process.bom'
    _description = 'MRP Process Bom'
    _inherit = ['mail.thread']
    _columns = {
        'name': fields.char('BOM Process Name', size=254, required=True, track_visibility='onchange'),
        'note': fields.text('Note'),
        'line_ids': fields.one2many('ineco.mrp.process.bom.line','process_bom_id','Lines'),
    }
    _sql_constraints = [
        ('name_unique',
         'unique (name)',
         'BOM Process name must be unique.')
    ]

    def copy(self, cr, uid, id, default=None, context=None):
        if context is None:
            context={}

        if not default:
            default = {}

        # Craft our own `<name> (copy)` in en_US (self.copy_translation()
        # will do the other languages).
        context_wo_lang = context.copy()
        context_wo_lang.pop('lang', None)
        bom = self.read(cr, uid, id, ['name'], context=context_wo_lang)
        default = default.copy()
        default.update(name="%s (copy)" % (bom['name']))
        return super(ineco_mrp_process_bom, self).copy(cr, uid, id, default=default, context=context)


class ineco_mrp_process_bom_line(osv.osv):
    _name = 'ineco.mrp.process.bom.line'
    _description = "Process Bom Detail"
    _columns = {
        'process_bom_id': fields.many2one('ineco.mrp.process.bom','BOM Process'),
        'sequence': fields.integer('Sequence'),
        'process_id': fields.many2one('ineco.mrp.process','Process'),
        'name': fields.char('Description',size=254),
    }
    _order = 'process_bom_id, sequence'
    _defaults = {
        'sequence': 100,
    }

class ineco_cutting_tag(osv.osv):

    def _get_product(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                #'product_name': False,
                'sale_product_id': False,
            }
            if obj.sale_order_id:
                sql = """
                    select
                      pt.name,
                      pp.id
                    from sale_order so
                    join sale_order_line sol on so.id = sol.order_id
                    join product_product pp on sol.product_id = pp.id
                    join product_template pt on pp.product_tmpl_id = pt.id
                    where so.id = %s and pt.type not in ('service')
                    limit 1
                """ % obj.sale_order_id.id
                cr.execute(sql)
                data = cr.fetchone()
                if data and data[0]:
                    #result[obj.id]['product_name'] = data[0] or ''
                    result[obj.id]['sale_product_id'] = data[1] or False
        return result

    def _get_quantity(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'order_qty': False
            }
            if obj.sale_order_id:
                sql = """
                    select
                      coalesce(sum(sol.product_uom_qty), 0) as quantity
                    from
                      sale_order_line sol
                      join product_product pp on sol.product_id = pp.id
                      join product_template pt on pt.id = pp.product_tmpl_id
                    where order_id = %s
                      and pt.type <> 'service'
                  """ % obj.sale_order_id.id
                cr.execute(sql)
                data = cr.fetchone()
                if data and data[0]:
                    result[obj.id]['order_qty'] = data[0] or 0.0
        return result

    def _get_tag_quantity(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'tag_quantity': False
            }
            total = 0.0
            for line in obj.line_ids:
                total += line.quantity
            result[obj.id]['tag_quantity'] = total
        return result

    _name = 'ineco.cutting.tag'
    _description = "Cutting Tag"
    _columns = {
        'name': fields.char('Cutting No', size=32, required=True),
        'sale_order_id': fields.many2one('sale.order','Sale Order'),
        'garment_order_no': fields.related('sale_order_id','garment_order_no', type="char", string="Garment No", readonly=True),
        'customer_id': fields.related('sale_order_id','partner_id',type="many2one", relation="res.partner", string="Customer", readonly=True),
        'sequence': fields.integer('Sequence'),
        'total': fields.integer('Total'),
        'date_start': fields.datetime('Date Start'),
        'date_finish': fields.datetime('Date Finish'),
        'machine_id': fields.many2one('ineco.mrp.machine','Cutting Table'),
        'sheet_length': fields.float('Sheet Length',digits=(12,2)),
        'sheet_quantity': fields.integer('Sheet Quantity'),
        'sheet_total': fields.float('Sheet Total', digits=(12,2)),
        'worker': fields.char('Worker', size=64),
        'color_code': fields.char('Color Code', size=64),
        'rolling': fields.boolean('Rolling'),
        'size_per_pattern': fields.integer('Size per Pattern'),
        'size_total': fields.float('Total'),
        'size_width': fields.float('Width'),
        'note': fields.text('Note'),
        'jfm': fields.char('JFM', size=64),
        'kpm': fields.char('KPM', size=64),
        'jiam': fields.char('Jiam', size=64),
        'cr': fields.char('CR', size=64),
        'st': fields.char('ST', size=64),
        'other': fields.char('Other', size=64),
        'order_qty': fields.function(_get_quantity, string="Quantity", type="integer", multi="_quantity"),
        'line_ids': fields.one2many('ineco.cutting.tag.line','cutting_id','Cutting Items'),
        'state': fields.selection([('draft','Draft'),('done','Done'),('cancel','Cancel')],'State',readonly=True),
        'sale_product_id': fields.function(_get_product, string="Product", type="many2one", relation="product.product", multi="_product",
            store = {
                'ineco.cutting.tag': (lambda self, cr, uid, ids, c={}: ids, [], 10),
            }),
        'tag_quantity': fields.function(_get_tag_quantity, string="Total", multi="_tag_quantity"),
    }
    _defaults = {
        'name': '/',
        'sequence': 1.0,
        #'date': time.strftime('%Y-%m-%d'),
        'total': 1.0,
        'state': 'draft',
    }

    def button_cancel(self, cr, uid, ids, context=None):
        for data in self.browse(cr, uid, ids):
            data.write({'state':'cancel'})
        return True

    def button_done(self, cr, uid, ids, context=None):
        for data in self.browse(cr, uid, ids):
            data.write({'state':'done'})
        return True

    def button_load(self, cr, uid, ids, context=None):
        sale_line_obj = self.pool.get('sale.order.line')
        cutting_tag_line_obj = self.pool.get('ineco.cutting.tag.line')
        for data in self.browse(cr, uid, ids):
            sale_line_ids = sale_line_obj.search(cr, uid, [('order_id','=',data.sale_order_id.id)])
            for sale_line in sale_line_obj.browse(cr, uid, sale_line_ids):
                if sale_line.order_line_property_other_ids:
                    for property in sale_line.order_line_property_other_ids:
                        found_ids = cutting_tag_line_obj.search(cr, uid, [('cutting_id','=',data.id),('property_id','=',property.id)])
                        if not found_ids:
                            new_data = {
                                'name': False,
                                'product_id': sale_line.product_id.id,
                                'property_id': property.id,
                                'cutting_id': data.id,
                            }
                            cutting_tag_line_obj.create(cr, uid, new_data)
        return True

    def button_reset(self, cr, uid, ids, context=None):
        obj_packing_line = self.pool.get('ineco.cutting.tag.line')
        for data in self.browse(cr, uid, ids):
            line_ids = obj_packing_line.search(cr, uid, [('cutting_id','=',data.id),('quantity','=',False)])
            if line_ids:
                obj_packing_line.unlink(cr, uid, line_ids)
        return True

    def create(self, cr, uid, vals, context=None):
        if vals.get('name','/')=='/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'ineco.cutting.tag') or '/'
        return super(ineco_cutting_tag, self).create(cr, uid, vals, context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if context is None:
            context = {}
        default = default.copy()
        default['line_ids'] = []
        default['name'] = self.pool.get('ir.sequence').get(cr, uid, 'ineco.cutting.tag')
        return super(ineco_cutting_tag, self).copy(cr, uid, id, default, context=context)

class ineco_cutting_tag_line(osv.osv):
    _name = 'ineco.cutting.tag.line'
    _description = "Cutting Tag Line"
    _columns = {
        'name': fields.char('Description', size=32),
        'cutting_id': fields.many2one('ineco.cutting.tag','Cutting Tag'),
        'property_id': fields.many2one('sale.line.property.other','Property'),
        'product_id': fields.many2one('product.product','Product'),
        'color_id': fields.related('property_id', 'color_id', type="many2one", relation='sale.color', string='Color',readonly=True),
        'gender_id': fields.related('property_id', 'gender_id', type="many2one", relation='sale.gender', string='Gender',readonly=True),
        'size_id': fields.related('property_id', 'size_id', type="many2one", relation='sale.size', string='Size',readonly=True),
        'note': fields.related('property_id','note', type="char", string="Note", readonly=True),
        'product_qty': fields.related('property_id', 'quantity', type="float",  string='Origin Qty',readonly=True),
        'quantity': fields.integer('Quantity'),
    }
