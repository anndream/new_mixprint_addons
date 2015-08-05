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

from openerp.osv import osv, fields
from openerp import tools

class ineco_sale_smart_delivery(osv.osv):
    _name = 'ineco.sale.smart.delivery'
    _auto = False
    _columns = {
    }
    _order = 'garment_order_no'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'ineco_sale_audit_delivery')
        cr.execute("""
        CREATE OR REPLACE VIEW ineco_sale_audit_delivery AS
            select 
              sp.id,
              concat(so.name,' (', next_garment_order_no,')') as garment_order_no,
              amount_untaxed,
              (select coalesce(sum(amount_untaxed),0.00) from account_invoice 
               where account_invoice.origin = so.name and
                 type = 'out_invoice' and
                 state not in ('cancel')) as invoice_amount_untaxed,
              sp.name,
              sp.batch_no,
              (select sum(product_uom_qty) from sale_order_line
               join product_product pp on pp.id = sale_order_line.product_id
               join product_template pt on pt.id = pp.product_tmpl_id
               where order_id = so.id and pt.type not in ('service')
              ) as sale_quantity,
              case 
                when sp.type = 'in' then -sp.quantity
                when sp.type = 'out' then sp.quantity
                else 
                  sp.quantity
              end as delivery_quantity,
              sp.account_internal_no,
              replace(
                replace(
		            replace(array(select garment_order_other from account_invoice
		                where account_invoice.garment_order_no = so.garment_order_no and
			                type = 'out_invoice' and
			                state not in ('cancel')
			                and garment_order_other is not null)::varchar,'}',''),
                 '{',''),'"','') as other_mo
            from 
              sale_order so
              left join stock_picking sp on sp.sale_id = so.id
            where 
              garment_order_date >= '2014-08-01'
              and so.state not in ('cancel')
              and sp.type not in ('internal')
              and sp.invoice_state = '2binvoiced'
              and so.amount_untaxed > 0
            order by
               so.garment_order_no,
               sp.batch_no
        """)
