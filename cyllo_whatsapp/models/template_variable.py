# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class TemplateVariable(models.Model):
    """Model representing Template Variables."""
    _name = 'template.variable'
    _description = 'Template Header and Body Variable'

    template_id = fields.Many2one('whatsapp.template', help='The template name of template variables')
    type = fields.Selection([('header', 'Header'), ('body', 'Body')], help='The type of template variable')
    display_name = fields.Char(help="""*The display name of variable. * Must be a unique name and can only contain 
    lowercase alphanumeric characters.""")
    sample_value = fields.Char(required=True, help='The sample value of variable')
    variable_value = fields.Char(string='Field Name', help='Enter the field name of selected model', required=True)
    model_id = fields.Many2one('ir.model', related='template_id.model_id',
                               help='The reference model for template')

    @api.constrains('variable_value')
    def _check_variable_value(self):
        """Check the validity of the variable_value field.
            Raises:
                ValidationError: If the 'variable_value' field contains an
                invalid field path, or if the user does not have read access to
                the referenced model.
            Returns:
                None """
        for record in self:
            model = self.env[self.model_id.model]
            if not model.check_access_rights('read', raise_exception=False):
                raise ValidationError(_("You are not allowed access the fields in %r."
                                        "\n Contact your administrator to request access if necessary.", model))
            variables = record.variable_value.split('.')
            for var in variables:
                if not hasattr(model, var):
                    raise ValidationError(_("Invalid field name: %r in %r", var, model._name))
