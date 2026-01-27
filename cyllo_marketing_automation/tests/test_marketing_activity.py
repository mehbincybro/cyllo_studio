# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import common


class TestMarketingActivity(common.TransactionCase):

    def test_compute_domain(self):
        """
            Test the _compute_domain method of the marketing.activity model.

            This test creates a marketing campaign, a parent activity, and a
            child activity. The child activity's _compute_domain method is then
            called, and the expected domain is compared with the actual domain
            set in the activity.
        """
        campaign = self.env['marketing.campaign'].create({
            'name': 'Campaign',
            'filter': '[("id", "=", 1)]'
        })
        parent_activity = self.env['marketing.activity'].create({
            'name': 'Activity 1',
            'campaign_id': campaign.id,
            'type': 'mail',
        })
        activity = self.env['marketing.activity'].create({
            'name': 'Activity 1',
            'campaign_id': campaign.id,
            'type': 'mail',
            'domain_activity': '[("id", "=", 1)]',
            'parent_activity_id': parent_activity.id
        })
        activity._compute_domain()
        expected_domain = ['&', ("id", "=", 1), ('id', '=', 1)]
        self.assertEqual(activity.domain, str(expected_domain))

    def test_marketing_execute(self):
        """
            Test the marketing_execute method of the marketing.activity model.

            This test creates a marketing campaign, a server activity, a
            participant, and an activity line associated with the campaign. The
            marketing_execute method is then called on the activity, and it is
            asserted that the state of the activity line is set to 'processed'.
        """
        campaign = self.env['marketing.campaign'].create(
            {'name': 'Campaign 1',
             'state': 'running'
             })
        activity = self.env['marketing.activity'].create({
            'name': 'Activity 1',
            'campaign_id': campaign.id,
            'type': 'server',
            'trigger_schedule_type': 'begin',
            'test_date_started': fields.datetime.now().replace(
                second=0, microsecond=0)
        })
        participant = self.env['marketing.participant'].create({
            'campaign_id': campaign.id,
            'record': 'res.partner,1',
            'record_id': 1,
            'is_test_participant': False
        })
        activity_line = self.env['marketing.activity.line'].create({
            'activity_id': campaign.activity_ids.id,
            'participant_id': participant.id,
            'state': 'schedule'
        })
        activity.marketing_execute()
        self.assertEqual(activity_line.state, 'processed')

    def test_test_participant_trigger(self):
        """
            Test the test_participant_trigger method of the marketing.activity
            model.

            This test creates a marketing campaign, a server activity, a
            participant, and an activity line associated with the campaign. The
            test_participant_trigger method is then called on the activity with
            the participant and activity line, and it is asserted that the
            result is True.
        """
        campaign = self.env['marketing.campaign'].create(
            {'name': 'Campaign 1',
             'state': 'running'
             })
        activity = self.env['marketing.activity'].create({
            'name': 'Activity 1',
            'campaign_id': campaign.id,
            'type': 'server',
            'trigger_schedule_type': 'begin',
            'test_date_started': fields.datetime.now().replace(
                second=0, microsecond=0)
        })
        participant = self.env['marketing.participant'].create({
            'campaign_id': campaign.id,
            'record': 'res.partner,1',
            'record_id': 1,
            'is_test_participant': False
        })
        activity_line = self.env['marketing.activity.line'].create({
            'activity_id': campaign.activity_ids.id,
            'participant_id': participant.id,
            'state': 'schedule'
        })
        result = activity.test_participant_trigger(participant, activity_line)
        self.assertTrue(result)

    def test_generate_schedule_trigger_next_activity(self):
        """
            Test the generate_schedule_trigger_next_activity method of the
            marketing.activity model.

            This test creates a marketing campaign, a server activity, a
            participant, and an activity line associated with the campaign. The
            generate_schedule_trigger_next_activity method is then called on
            the activity with the participant, and it is asserted that
            the cron_id of the resulting schedule is the expected cron.
        """
        campaign = self.env['marketing.campaign'].create(
            {'name': 'Campaign 1',
             'state': 'running'
             })
        activity = self.env['marketing.activity'].create({
            'name': 'Activity 1',
            'campaign_id': campaign.id,
            'type': 'server',
            'trigger_schedule_type': 'activity_another',
            'test_date_started': fields.datetime.now().replace(
                second=0, microsecond=0)
        })
        participant = self.env['marketing.participant'].create({
            'campaign_id': campaign.id,
            'record': 'res.partner,1',
            'record_id': 1,
            'is_test_participant': False
        })
        self.env['marketing.activity.line'].create({
            'activity_id': campaign.activity_ids.id,
            'participant_id': participant.id,
            'state': 'schedule'
        })
        cron = self.env.ref(
            'cyllo_marketing_automation.ir_cron_marketing_automation_run_activity')
        result = activity.generate_schedule_trigger_next_activity(activity,
                                                                  participant)
        self.assertEqual(result.cron_id, cron)

    def test_execute_server(self):
        """
            Test the _execute_server method of the marketing.activity model.

            This test creates a marketing campaign, a server activity, a
            participant, and an activity line associated with the campaign. The
            execute_server method is then called on the activity with the
            participant and activity line, and it is asserted that the
            participant is marked as inactive and the activity line
            state is 'processed'.
        """
        campaign = self.env['marketing.campaign'].create(
            {'name': 'Campaign 1',
             'state': 'running'
             })
        activity = self.env['marketing.activity'].create({
            'name': 'Activity 1',
            'campaign_id': campaign.id,
            'type': 'server',
            'trigger_schedule_type': 'activity_another',
            'test_date_started': fields.datetime.now().replace(
                second=0, microsecond=0)
        })
        participant = self.env['marketing.participant'].create({
            'campaign_id': campaign.id,
            'record': 'res.partner,1',
            'record_id': 1,
            'is_test_participant': False,
            'is_inactive': False
        })
        activity_line = self.env['marketing.activity.line'].create({
            'activity_id': campaign.activity_ids.id,
            'participant_id': participant.id,
            'state': 'schedule'
        })
        activity._execute_server(participant, activity, activity_line)
        self.assertTrue(participant.is_inactive)
        self.assertEqual(activity_line.state, 'processed')

    def test_execute_mail(self):
        """
            Test the _execute_mail method of the marketing.activity model.

            This test creates a marketing campaign, a server activity, a
            participant, and an activity line associated with the campaign.
            The activity line is updated with a mail trace, and the
            _execute_mail method is then called on the activity with the
            participant and activity line. It is asserted that the
            activity line state is 'processed' and the result is True.
        """
        campaign = self.env['marketing.campaign'].create(
            {'name': 'Campaign 1',
             'state': 'running'
             })
        activity = self.env['marketing.activity'].create({
            'name': 'Activity 1',
            'campaign_id': campaign.id,
            'type': 'server',
            'trigger_schedule_type': 'activity_another',
            'test_date_started': fields.datetime.now().replace(
                second=0, microsecond=0)
        })
        participant = self.env['marketing.participant'].create({
            'campaign_id': campaign.id,
            'record': 'res.partner,1',
            'record_id': 1,
            'is_test_participant': False,
            'is_inactive': False
        })
        activity_line = self.env['marketing.activity.line'].create({
            'activity_id': campaign.activity_ids.id,
            'participant_id': participant.id,
            'state': 'schedule'
        })
        activity_line.write({
            'mail_trace_ids': [(0, 0, {'model': 'res.partner',
                                       'record_id': self.env.ref(
                                           'hr.work_contact_mit').id,
                                       'marketing_activity_line_id': activity_line.id,
                                       })]
        })
        result = activity._execute_mail(participant, activity, activity_line)
        self.assertEqual(activity_line.state, 'processed')
        self.assertTrue(result)

    def test_execute_actions(self):
        campaign = self.env['marketing.campaign'].create(
            {'name': 'Campaign 1',
             'state': 'running'
             })
        activity = self.env['marketing.activity'].create({
            'name': 'Activity 1',
            'campaign_id': campaign.id,
            'type': 'server',
            'trigger_schedule_type': 'begin',
            'test_date_started': fields.datetime.now().replace(
                second=0, microsecond=0)
        })
        participant = self.env['marketing.participant'].create({
            'campaign_id': campaign.id,
            'record': 'res.partner,1',
            'record_id': 1,
            'is_test_participant': False,
            'is_inactive': False
        })
        activity_line = self.env['marketing.activity.line'].create({
            'activity_id': campaign.activity_ids.id,
            'participant_id': participant.id,
            'state': 'schedule'
        })
        activity.execute_actions(participant)
        self.assertEqual(activity_line.state, 'processed')
