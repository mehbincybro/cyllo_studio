# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo.tests import common
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class TestHelpdeskFeatures(common.TransactionCase):

    def setUp(self):
        super(TestHelpdeskFeatures, self).setUp()
        self.Team = self.env['helpdesk.team']
        self.Ticket = self.env['helpdesk.ticket']
        self.Partner = self.env['res.partner']
        self.Skill = self.env['helpdesk.skill']
        
        self.partner = self.Partner.create({'name': 'Test Customer'})
        self.team = self.Team.create({
            'name': 'Support Team',
            'assignment_method': 'skill',
        })
        self.skill_it = self.Skill.create({'name': 'IT'})
        
        self.user_tech = self.env['res.users'].create({
            'name': 'Tech User',
            'login': 'tech_user',
            'email': 'tech@example.com',
            'groups_id': [(6, 0, [self.env.ref('cyllo_help_desk.cyllo_help_desk_user').id])],
            'helpdesk_skill_ids': [(6, 0, [self.skill_it.id])]
        })

    def test_01_parent_child_linking(self):
        """ Test that closing a parent ticket closes its children """
        parent = self.Ticket.create({
            'name': 'Parent Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
        })
        child = self.Ticket.create({
            'name': 'Child Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
            'parent_id': parent.id,
        })
        
        solved_stage = self.env.ref('cyllo_help_desk.solved_ticket')
        parent.stage_id = solved_stage.id
        parent.onchange_stage_id() # Trigger logic manually in test
        
        self.assertEqual(child.stage_id.id, solved_stage.id, "Child ticket should be solved when parent is solved")

    def test_02_ticket_dependencies(self):
        """ Test that a ticket cannot be closed if dependencies are unresolved """
        dep = self.Ticket.create({
            'name': 'Dependency',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
        })
        main_ticket = self.Ticket.create({
            'name': 'Main Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
            'dependency_ids': [(6, 0, [dep.id])]
        })
        
        solved_stage = self.env.ref('cyllo_help_desk.solved_ticket')
        with self.assertRaises(UserError):
            main_ticket.stage_id = solved_stage.id
            main_ticket.onchange_stage_id()

    def test_03_skill_based_assignment(self):
        """ Test that tickets are assigned based on skills """
        ticket = self.Ticket.create({
            'name': 'IT Issue',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
            'skill_ids': [(6, 0, [self.skill_it.id])],
            'user_id': False, # Force assignment logic
        })
        # Note: creation triggers _assign_ticket
        self.assertEqual(ticket.user_id.id, self.user_tech.id, "Ticket should be assigned to the user with matching skill")

    def test_04_sla_pause(self):
        """ Test SLA pause toggle """
        ticket = self.Ticket.create({
            'name': 'SLA Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
        })
        ticket.action_toggle_sla_pause()
        self.assertTrue(ticket.sla_paused)
        self.assertTrue(ticket.sla_pause_date)
        
        ticket.action_toggle_sla_pause()
        self.assertFalse(ticket.sla_paused)
