# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-Today INECO LTD., Part. (<http://www.ineco.co.th>).
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

from openerp.osv import fields, osv

class sale_order(osv.osv):

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
                      and ai.saleorder_id = so.id) as invoice_count,
                   (select count(*) from account_invoice ai
                    where type = 'out_refund'
                      and state = 'paid'
                      and ai.saleorder_id = so.id) as refund_count,
                   (select coalesce(sum(amount_untaxed),0.00) from account_invoice ai
                    where type = 'out_invoice'
                      and state = 'paid'
                      and ai.saleorder_id = so.id) as invoice_amount,
                   (select coalesce(sum(amount_untaxed),0.00) from account_invoice ai
                    where type = 'out_refund'
                      and state = 'paid'
                      and ai.saleorder_id = so.id) as refund_amount
                from
                   sale_order so
                where
                  so.state not in ('draft','cancel') and
                  so.id = %s
                  and so.next_garment_order_no is not null
                  and amount_untaxed - (select coalesce(sum(amount_untaxed),0.00) from account_invoice ai
                    where type = 'out_refund'
                      and ai.saleorder_id = so.id) <= (select coalesce(sum(amount_untaxed),0.00) from account_invoice ai
                    where type = 'out_invoice'
                      and ai.saleorder_id = so.id)
              """ % obj.id
            cr.execute(sql)
            data = cr.fetchone()
            if data and data[0]:
                result[obj.id]['commission_ready'] = data[2] - data[6] <= data[5]
        return result

    def _get_invoice_paid(self, cr, uid, ids, context=None):
        result = {}
        for data in self.pool.get('account.invoice').browse(cr, uid, ids, context=context):
            result[data.saleorder_id.id] = True
        return result.keys()

    _inherit = 'sale.order'
    _columns = {
        'next_garment_order_no': fields.char('Garment Order No', size=32),
        'next_garment_order_date': fields.date('Garment Order Date'),
        'next_sample_order_no': fields.char('Sampling Order No', size=32),
        'candidate_ids': fields.one2many('sale.order.candidate','order_id','Candidates'),
        'commission_ready': fields.function(_get_commission, string="Commission Ready",
                    store={
                        'sale.order': (lambda self, cr, uid, ids, c={}: ids, [], 10),
                        'account.invoice': (_get_invoice_paid, ['state'], 10),
                    },
                    type="boolean", multi="_commission"),
    }
    
class sale_order_candidate(osv.osv):
    _name = 'sale.order.candidate'
    _description = "Candidate Material"
    _columns = {
        'name': fields.char('Description',size=64,required=True),
        'cost': fields.integer('Unit Price'),
        'order_id': fields.many2one('sale.order','Sale Order'),
    }
    _defaults = {
        'cost': 1.0,
    }