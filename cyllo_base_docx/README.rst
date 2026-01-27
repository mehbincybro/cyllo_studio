Base Docx Report
=================
This module provides a way to Generate DOCX report.

Usage
=====
To use this Module you need to return following action with list of actions to execute:


* Add DOCX button function in module
* data - Add the values for the report
* 'model' - Name of the model where function "get_docx_report" defined
* 'output_format' - formate of the report
* 'report_name' - Name of the Report(blank space is not supported)
.. code-block:: python
        def action_print_docx(self):
            data = {
                'name': self.name,
            }
            return {
                'type': 'ir.actions.report',
                'data': {
                    'model': 'res.partner', # your.model
                    'options': json.dumps(data, default=date_utils.json_default),
                    'output_format': 'docx',
                    'report_name': 'DocsReport',
                },
                'report_type': 'docx',
            }

* DOCX report Function
 In this generate an DOCX report based on the provided data and write it to the response.
.. code-block:: python
    def get_docx_report(self, document, data):
        document.add_paragraph(data['name'])
        return document
