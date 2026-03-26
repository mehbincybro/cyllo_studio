# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
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
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    def _archive_whatsapp_workflows_before_uninstall(self):
        """
                Archive workflows containing WhatsApp nodes before uninstalling the 'cyllo_whatsapp' module.

                This method checks whether the module being uninstalled is 'cyllo_whatsapp'.
                If so, it searches for workflows that include WhatsApp-related nodes and archives them
                using a helper method from the 'work.auto' model.

                It also logs the number of workflows archived along with their names for tracking purposes.

                Returns:
                    None
                """
        if not any(module.name == 'cyllo_whatsapp' for module in self):
            return

        archived_workflows = self.env['work.auto'].sudo()._archive_workflows_with_whatsapp_nodes()
        if archived_workflows:
            _logger.info(
                "Archived %s workflow(s) containing WhatsApp nodes before uninstalling cyllo_whatsapp: %s",
                len(archived_workflows),
                ", ".join(archived_workflows.mapped('name')),
            )

    def button_uninstall(self):
        """
                Override the default uninstall button action to ensure WhatsApp workflows are archived.

                This method calls the workflow archiving logic before proceeding with the standard
                module uninstallation process.

                Returns:
                    Any: Result of the parent class's button_uninstall method.
                """
        self._archive_whatsapp_workflows_before_uninstall()
        return super().button_uninstall()

    def button_immediate_uninstall(self):
        """
                Override the immediate uninstall action to archive WhatsApp workflows beforehand.

                This method ensures that workflows containing WhatsApp nodes are archived even when
                the module is uninstalled immediately, bypassing the usual uninstall flow.

                Returns:
                    Any: Result of the parent class's button_immediate_uninstall method.
                """
        self._archive_whatsapp_workflows_before_uninstall()
        return super().button_immediate_uninstall()
