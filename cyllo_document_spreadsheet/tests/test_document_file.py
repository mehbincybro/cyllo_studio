# -*- coding: utf-8 -*-
import logging
from odoo.tests import common
import datetime

_LOGGER = logging.getLogger(__name__)


class TestDocumentFile(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _LOGGER.info("Starts setUpClass of 'document.file'")
        workspace_id = cls.env.ref(
            "cyllo_document_spreadsheet.document_workspace_spreadsheet").id
        cls.document = cls.env['document.file'].create({
            'workspace_id': workspace_id,
            'is_excel': False,
        })
        cls.spreadsheet_id = cls.env['spreadsheet.spreadsheet'].create({
            'name': 'Test name',
            'document_file_id': cls.document.id,
            'is_document': True,
        })
        cls.args = ({'file':
                         'UEsDBBQAAAAIAAAAIQARN5q/EAIAALMFAAAYAAAAeGwvd29ya3No'
                         'ZWV0cy9zaGVldDEueG1sjVTLjpswFN33KyzviyGERyJgNGU0aheV'
                         'qk4fawcuDw3YyHaS6d/XBpIhwEjZRPieex7XsR09vLUNOoGQNWcx'
                         'diwbI2AZz2tWxvj3r+fPIUZSUZbThjOI8T+Q+CH5FJ25eJUVgEJa'
                         'gMkYV0p1e0JkVkFLpcU7YBopuGip0ktREtkJoHlPahuysW2ftLRm'
                         'eFDYi3s0eFHUGTzx7NgCU4OIgIYqHV9WdSdxEuW1xsw8SEAR40dnn'
                         '+4wSaLe+U8NZzn5RooeXqCBTEGu58fIDHbg/NWA33TJNlSy4D73o'
                         'X4IlENBj436yc9foS4rpUU8Q8l4I/tf1NasV27p2+BQ56qKsWdbg'
                         'WPv3MDDKDtKxdu/A+CM9IG4GYmbK9G5j+iORPdOIhkS99M9UUWTS'
                         'PAzEn1k2VHzHzt7V+9vZoqPptpjemKz66fEjsjJyIwdXy4dZCykk'
                         'wLR2lcDd9XAnUg7M+kptrliN6LbVdFtTzys5l3HbkT9VVF/sRXuT'
                         'HrZsb3tSJcd3nqEYDVCMCH6M/Ng2MLN1rNnI6cjFPrBB27hqlu4C'
                         'BvMPJcd84GXHR9E2K1G2E2I4cx8N8gFjjU7N+mAhJ7lBzMzMjn3L'
                         'YgSUmgaiTJ+ZOZK40n1/VkZjvJ7exJ1tITvVJQ1k6iBQlP1ncNID'
                         'C9D/61413/pS3jgSl/Cy6rSryMIs9LHu+BcXRbG5PreJv8BUEsDB'
                         'BQAAAAIAAAAIQAWcXNoUAEAACoCAAAPAAAAeGwvd29ya2Jvb2sue'
                         'G1sjVHLbsIwELz3K6y9lzyURAWRoD6oilQVhFLo1Y03xMKxI9tp4'
                         'O/rBIW2t552Z7wz2lnPF6dakC/UhiuZQjDxgaAsFOPykMJ7/nx7B'
                         '8RYKhkVSmIKZzSwyG7mndLHT6WOxOmlSaGytpl5nikqrKmZqAale'
                         'ymVrql1UB8802ikzFSIthZe6PuJV1Mu4eIw0//xUGXJC3xSRVujt'
                         'BcTjYJat72peGMgm5dc4O4SiNCmeaO1W/skgAhq7JJxiyyFyEHV4'
                         'R9Ct81Dy0UPYj8GL7uG3GjCsKStsLlbbXR35wqjMEz6yX5qx7EzP'
                         '6IektOeS6a6FMLIXfY8oiAG0g39njNbOSLxp1fuBfmhsilMk8Tvz'
                         'b1f7sP9xkrkEC6//yDb5Wa9zd1f9fzKZQhcoBl3jV6xYHAZpQUVh'
                         'UvUl2EwjOJgCqRshXh03Fq+KjoY9KIxTfYNUEsDBBQAAAAIAAAAIQ'
                         'DLnvSVywAAAGkBAAAUAAAAeGwvc2hhcmVkU3RyaW5ncy54bWxt0M'
                         'FqwzAMBuD7nsIIdlydFDa64biMsh630mWwq0nUxhDLmaWM9u3rUn'
                         'ZJdtT380sgsz6FXv1iYh+pgnJRgEJqYuvpWMFXvX1YgWJx1Lo+El'
                         'ZwRoa1vTPMonKVuIJOZHjRmpsOg+NFHJBycogpOMljOmoeErqWO0'
                         'QJvV4WxZMOzhOoJo4k+WwJaiT/M+LmBs9gDXtrxNav32r/tvvY10'
                         'aLNfqqt2SbYphaHafy6Xqc2jvKrOhO/5AqH++nvBtT0zmeLf1zNe'
                         'vp/Ct7AVBLAwQUAAAACAAAACEAVSvwo34BAAAUAwAAEAAAAGRvY1B'
                         'yb3BzL2FwcC54bWydUsFO4zAQve9XRL5TpxVaocoxQgXEYVdUNMBe'
                         'jTNpLBzb8gxRy9evk6ppuuwJn968eXp+Ho+43rU26yCi8a5g81n'
                         'OMnDaV8ZtC/Zc3l9csQxJuUpZ76Bge0B2LX+IdfQBIhnALDk4LFh'
                         'DFJaco26gVThLbZc6tY+tolTGLfd1bTTcev3RgiO+yPOfHHYEroL'
                         'qIoyG7OC47Oi7ppXXfT58Kfch+UlxE4I1WlF6pPxtdPToa8rudhq'
                         's4NOmSEYb0B/R0F7mgk9LsdHKwioZy1pZBMFPhHgA1c9srUxEKTpa'
                         'dqDJxwzNZ5ragmVvCqGPU7BORaMcsYPsUAzYBqQoX318xwaAUPCR'
                         'HOBUO8XmUs4HQQLnQj4GSfg8YmnIAj7WaxXpP4nn08RDBjbJWN7'
                         '8yZ7u1o9P5ZeMx9v+8V/5NiiXhshH9Mu4d3wOpb9VBMeRnpNi06g'
                         'IVfqFceQjIR5Stmh7/apRbgvVUfO10S/Ay2HJ5Xwxy9MZ/v3ICX7'
                         'aZ/kXUEsDBBQAAAAIAAAAIQA+0rd4JQEAAFACAAARAAAAZG9jUHJ'
                         'vcHMvY29yZS54bWydks1OwzAQhO88ReR74rgBiqwklQD1RCUkikDc'
                         'LHvbWsQ/sg1p3h4nadNW6onjema/nV25XOxVk/yC89LoCpEsRwlob'
                         'oTU2wq9r5fpA0p8YFqwxmioUAceLeqbklvKjYNXZyy4IMEnEaQ95b'
                         'ZCuxAsxdjzHSjms+jQUdwYp1iIpdtiy/g32wKe5fk9VhCYYIHhHp'
                         'jaiYgOSMEnpP1xzQAQHEMDCnTwmGQEn7wBnPJXGwblzKlk6CxctR'
                         '7Fyb33cjK2bZu1xWCN+Qn+XL28DaumUven4oDqUnDKHbBgXF3i8y'
                         'IermE+rOKJNxLEYxf1K2+HRcY+EEkMQMe4R+WjeHpeL1E9y2dFSk'
                         'hK5uv8lhZ3lMy/+pEX/SegOgz5N/EIGHNffoL6D1BLAwQUAAAACA'
                         'AAACEAYV1JOk8BAACPBAAAEwAAAFtDb250ZW50X1R5cGVzXS54bW'
                         'ytlMtuwjAQRff9isjbKjF0UVUVgUUfyxap9ANce0IsHNvyDBT+vp'
                         'PwUFtRoIJNrGTu3HPHjjwYLRuXLSChDb4U/aInMvA6GOunpXifPO'
                         'd3IkNS3igXPJRiBShGw6vBZBUBM272WIqaKN5LibqGRmERIniuVC'
                         'E1ivg1TWVUeqamIG96vVupgyfwlFPrIYaDR6jU3FH2tOTP6yAJHI'
                         'rsYS1sWaVQMTqrFXFdLrz5Rck3hII7Ow3WNuI1C4TcS2grfwM2fa'
                         '+8M8kayMYq0YtqWCVN0OMUIkrWF4dd9sQMVWU1sMe84ZYC2kAGTB'
                         '7ZEhJZ2GU+yNYhwf/h2z1qu08kLp1EWjnAs0fFmEAZrAGoccXa9'
                         'AiZ+H+C9bN/Nr+zOQL8DGn2EcLs0sO2a9Eo60/gd2KU3XL+1D+D7P'
                         'yPHXmtEpg3SnwNXPzkv3tvc8juPhl+AVBLAwQUAAAACAAAACEAeM'
                         'JEAe8BAADMBAAADQAAAHhsL3N0eWxlcy54bWy9VFuL1DAUfvdXhL'
                         'y7nXZ1UGm7yEpBUBF2BF/TJm0DuZTkzNDur/ek6WUGXBQfpNCc8+'
                         'V837lw2vxh1IpchPPSmoKmdwdKhGksl6Yr6I9T9fodJR6Y4UxZI'
                         'wo6CU8fyle5h0mJp14IIKhgfEF7gOFDkvimF5r5OzsIgzetdZoB'
                         'uq5L/OAE4z6QtEqyw+GYaCYNLfPWGvCksWcDBc0WoMz9M7kwhWWlN'
                         'CnzxirrCKA81jEjhmkRIx6ZkrWTAWyZlmqKcBaAuaIlTktjXQCTmC'
                         'G+6+R/5JoPjySp1NbsPY1AmQ8MQDhToUMW+zQNmN7g4KPMHPeH6M'
                         '6xKc3e/j3BWyV5qKJ7nJt2XV3Qqvp0H54gUy8X0nAxCl7Q45tZ/Up'
                         'xyzUf2GNtHcelWrtM6QqVuRItIN3Jrg8n2CHksABWo8El66xhKiR'
                         'YGYuBso1Q6ils3s/2RntsiTnrSsNnLA9XOEx6NbGgxYwy0Qn612p'
                         'R+0o2+ydZMrab/kvsdGdnL7AJGwY1VTb2t3jI2b2PSnZGi3UAbHVJ'
                         'b518RmLYwAYBEVdwbJeGt17nzm+muKEkLHtBv4VvV11VVZ+lAml+'
                         'M0HU5OM+vPkWWI2/iJssqMFFy84KTttlQXf7q+DyrN9vUd/lxcIS'
                         'tdtfwuqkx7mC/T9U/gJQSwMEFAAAAAgAAAAhABj6RlSwBQAAUhsAA'
                         'BMAAAB4bC90aGVtZS90aGVtZTEueG1s7VlNj9tEGL7zK0a+t44TO8'
                         '2umq022aSF7bar3bSox4k9sacZe6yZyW5zQ+0RCQlREBckbhwQUKm'
                         'VuJRfs1AERepf4PVHkvFmss22iwC1OSSe8fN+f/gd5+q1BzFDR0RI'
                         'ypO25VyuWYgkPg9oEratO4P+pZaFpMJJgBlPSNuaEmld2/rgKt5UE'
                         'YkJAvJEbuK2FSmVbtq29GEby8s8JQncG3ERYwVLEdqBwMfANmZ2vV'
                         'Zr2jGmiYUSHAPX26MR9QkaZCytrRnzHoOvRMlsw2fi0M8l6hQ5Nhg'
                         '72Y+cyi4T6AiztgVyAn48IA+UhRiWCm60rVr+seytq/aciKkVtBp'
                         'dP/+UdCVBMK7ndCIczgmdvrtxZWfOv17wX8b1er1uz5nzywHY98F'
                         'SZwnr9ltOZ8ZTAxWXy7y7Na/mVvEa/8YSfqPT6XgbFXxjgXeX8K1'
                         'a092uV/DuAu8t69/Z7nabFby3wDeX8P0rG023is9BEaPJeAmdxXM'
                         'emTlkxNkNI7wF8NYsARYoW8uugj5Rq3Itxve56AMgDy5WNEFqmpI'
                         'R9gHXxfFQUJwJwJsEa3eKLV8ubWWykPQFTVXb+ijFUBELyKvnP7x'
                         '6/hS9ev7k5OGzk4c/nzx6dPLwJwPhDZyEOuHL7z7/65tP0J9Pv33'
                         '5+EszXur433789NdfvjADlQ588dWT3589efH1Z398/9gA3xZ4qMMH'
                         'NCYS3SLH6IDHYJtBABmK81EMIkwrFDgCpAHYU1EFeGuKmQnXIVXn3'
                         'RXQAEzA65P7FV0PIzFR1ADcjeIKcI9z1uHCaM5uJks3Z5KEZuFiou'
                         'MOMD4yye6eCm1vkkImUxPLbkQqau4ziDYOSUIUyu7xMSEGsnuUVvy'
                         '6R33BJR8pdI+iDqZGlwzoUJmJbtAY4jI1KQihrvhm7y7qcGZiv0O'
                         'OqkgoCMxMLAmruPE6nigcGzXGMdORN7GKTEoeToVfcbhUEOmQMI5'
                         '6AZHSRHNbTCvq7mLoRMaw77FpXEUKRccm5E3MuY7c4eNuhOPUqDN'
                         'NIh37oRxDimK0z5VRCV6tkGwNccDJynDfpUSdr6zv0DAyJ0h2ZyLK'
                         'rl3pvzFNzmrGjEI3ft+MZ/BteDSZSuJ0C16F+x823h08SfYJ5Pr7'
                         'vvu+776LfXdVLa/bbRcN1tbn4pxfvHJIHlHGDtWUkZsyb80SlA76'
                         'sJkvcqL5TJ5GcFmKq+BCgfNrJLj6mKroMMIpiHFyCaEsWYcSpVzC'
                         'ScBayTs/TlIwPt/zZmdAQGO1x4Niu6GfDeds8lUodUGNjMG6whpX'
                         '3k6YUwDXlOZ4ZmnemdJszZtQDQhnB3+nWS9EQ8ZgRoLM7wWDWVgu'
                         'PEQywgEpY+QYDXEaa7qt9XqvadI2Gm8nbZ0g6eLcFeK8C4hSbSlK9'
                         'nI5sqS6QseglVf3LOTjtG2NYJKCyzgFfjJrQJiFSdvyVWnKa4v5tM'
                         'HmtHRqKw2uiEiFVDtYRgVVfmv26iRZ6F/33MwPF2OAoRutp0Wj5fy'
                         'LWtinQ0tGI+KrFTuLZXmPTxQRh1FwjIZsIg4w6O0W2RVQCc+M+mwh'
                         'oELdMvGqlV9WwelXNGV1YJZGuOxJLS32BTy/nuuQrzT17BW6v6Ep'
                         'jQs0xXt3TckyF8bWRpAfqGAMEBhlOdq2uFARhy6URtTvCxgcclmgF'
                         '4KyyFRCLHvfnOlKjhZ9q+BRNLkwUgc0RIJCp1ORIGRflXa+hplT15'
                         '+vM0Zln5mrK9Pid0iOCBtk1dvM7LdQNOsmpSNy3Omg2abqGob9//'
                         'Dk466YfM4eDxaC3PPMIq7W9LVHwcbbqXDOR23dbHHdW/tRm8LhA2'
                         'Vf0Lip8Nlivh3wA4g+mk+UCBLxUqssv/nmEHRuacZlrP7ZMWoRgt'
                         'aKeF/k8Kk5u7HC2WeLe3NnewZfe2e72l4uUVs7yOSrpT+e+PA+yN'
                         '6Bg9KEKVm8TXoAR83u7C8D4GMvSLf+BlBLAwQUAAAACAAAACEA8p'
                         '9J2ukAAABLAgAACwAAAF9yZWxzLy5yZWxzrZLBTsMwDEDvfEXk+5'
                         'puSAihpbsgpN0mND7AJG4btY2jxIPu74mQQAyNaQeOceznZ8vrzT'
                         'yN6o1S9hwMLKsaFAXLzofOwMv+aXEPKgsGhyMHMnCkDJvmZv1MI0'
                         'qpyb2PWRVIyAZ6kfigdbY9TZgrjhTKT8tpQinP1OmIdsCO9Kqu73T'
                         '6yYDmhKm2zkDauiWo/THSNWxuW2/pke1hoiBnWvzKKGRMHYmBedTv'
                         'nIZX5qEqUNDnXVbXu/w9p55I0KGgtpxoEVOpTuLLWr91HNtdCefP'
                         'jEtCt/+5HJqFgiN3WQlj/DLSJzfQfABQSwMEFAAAAAgAAAAhAER1W'
                         '/DoAAAAuQIAABoAAAB4bC9fcmVscy93b3JrYm9vay54bWwucmVsc6'
                         '2SwWrDMBBE7/0KsfdadhJKKZFzKYVc2/QDhLS2TGxJaLdp/fcRCU0'
                         'dCKEHn8SM2JkHu+vNz9CLAybqgldQFSUI9CbYzrcKPndvj88giLW'
                         '3ug8eFYxIsKkf1u/Ya84z5LpIIod4UuCY44uUZBwOmooQ0eefJqR'
                         'Bc5aplVGbvW5RLsrySaZpBtRXmWJrFaStrUDsxoj/yQ5N0xl8DeZ'
                         'rQM83KuR3SHtyiJxDdWqRFVwskqenKnIqyNswizlhOM/iH8hJns27'
                         'DMs5GYjHPi/0AnHW9+pXs9Y7ndB+cMrXNqWY2r8w8uri6iNQSwECF'
                         'AMUAAAACAAAACEAETeavxACAACzBQAAGAAAAAAAAAAAAAAAgAEAAA'
                         'AAeGwvd29ya3NoZWV0cy9zaGVldDEueG1sUEsBAhQDFAAAAAgAAAA'
                         'hABZxc2hQAQAAKgIAAA8AAAAAAAAAAAAAAIABRgIAAHhsL3dvcmti'
                         'b29rLnhtbFBLAQIUAxQAAAAIAAAAIQDLnvSVywAAAGkBAAAUAAAAA'
                         'AAAAAAAAACAAcMDAAB4bC9zaGFyZWRTdHJpbmdzLnhtbFBLAQIUAx'
                         'QAAAAIAAAAIQBVK/CjfgEAABQDAAAQAAAAAAAAAAAAAACAAcAEAAB'
                         'kb2NQcm9wcy9hcHAueG1sUEsBAhQDFAAAAAgAAAAhAD7St3glAQAA'
                         'UAIAABEAAAAAAAAAAAAAAIABbAYAAGRvY1Byb3BzL2NvcmUueG1sU'
                         'EsBAhQDFAAAAAgAAAAhAGFdSTpPAQAAjwQAABMAAAAAAAAAAAAAAI'
                         'ABwAcAAFtDb250ZW50X1R5cGVzXS54bWxQSwECFAMUAAAACAAAACE'
                         'AeMJEAe8BAADMBAAADQAAAAAAAAAAAAAAgAFACQAAeGwvc3R5bGVz'
                         'LnhtbFBLAQIUAxQAAAAIAAAAIQAY+kZUsAUAAFIbAAATAAAAAAAAA'
                         'AAAAACAAVoLAAB4bC90aGVtZS90aGVtZTEueG1sUEsBAhQDFAAAA'
                         'AgAAAAhAPKfSdrpAAAASwIAAAsAAAAAAAAAAAAAAIABOxEAAF9yZW'
                         'xzLy5yZWxzUEsBAhQDFAAAAAgAAAAhAER1W/DoAAAAuQIAABoAAAA'
                         'AAAAAAAAAAIABTRIAAHhsL19yZWxzL3dvcmtib29rLnhtbC5yZWxz'
                         'UEsFBgAAAAAKAAoAgAIAAG0TAAAAAA==',
                     'file_name': 'Tax report.xlsx',
                     'workspace_id': 1})
        _LOGGER.info("End setUpClass")

    def test_for_fields(self):
        """Test for the fields in 'document.file''"""
        _LOGGER.info("Starts field test for 'document.file'")
        self.assertEqual(self.document.is_excel, False)
        _LOGGER.info("End 'document.file' fields test")

    def test_open_spreadsheet(self):
        """Test for open_spreadsheet function. """
        _LOGGER.info("Starts test for open_spreadsheet function.")
        document_id = self.env['document.file'].search([], limit=1)
        file = {'defaultSource': 'http://test:8017/web/image/1847'
                                 '?unique=825387c05d27cd359e3dd76247fbf0dc'
                                 '08a0ae9f',
                'displayName': 'Event Management Report.xlsx',
                'downloadUrl': 'http://test:8017/web/image/1847?unique'
                               '=825387c05d27cd359e3dd76247fbf0dc08a0ae9f',
                'extension': 'xlsx',
                'filename': 'Event Management Report.xlsx',
                'id': document_id.id,
                'originThreadLocalId': 'document.file,' + str(document_id.id),
                'uid': '2',
                'isPdf': False,
                'isImage': False,
                'isViewable': False,
                'mimetype': 'application/vnd.openxmlformats-officedocument'
                            '.spreadsheetml.sheet',
                'urlRoute': '/web/image/1849'}
        spreadsheet_id = self.env['spreadsheet.spreadsheet'].sudo().search(
            [('document_file_id', '=', file.get('id'))]).id
        result = self.document.open_spreadsheet(file)
        self.assertEqual(result, spreadsheet_id)
        _LOGGER.info("End open_spreadsheet function test.")

    def test_action_upload_document(self):
        """Test for action_upload_document function. """
        _LOGGER.info("Starts test for action_upload_document function.")
        self.document.action_upload_document(self.args)
        self.assertEqual(self.env['document.file'].search([], order='id desc',
                                                          limit=1)
                         .workspace_id.id, 2)
        _LOGGER.info("End action_upload_document function test.")

    def test_create(self):
        """Test for create function. """
        _LOGGER.info("Starts test for 'create' function.")
        date = datetime.datetime(
            2023, 12, 11, 4, 17, 3)
        vals_list = [{'name': 'Test spreadsheet', 'date': date,
                      'extension': 'xlsx', 'workspace_id': 2, 'is_excel': True}]
        self.document.extension = 'xlsx'
        result = self.document.create(vals_list)
        self.assertEqual(result.name, self.env['ir.attachment']
                         .sudo().search([], order='id desc', limit=1).name)
        self.assertEqual(result, self.env['document.file'].
                         search([], order='id desc', limit=1))
        self.assertEqual(result.name, 'Test spreadsheet')
        self.assertEqual(result.date, date)
        self.assertEqual(result.extension, 'xlsx')
        self.assertEqual(result.workspace_id.id, 2)
        self.assertEqual(result.is_excel, True)
        _LOGGER.info("End 'create' function test.")
