/** @odoo-module **/
import { registry } from "@web/core/registry";
import { onWillStart, onMounted, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
const actionRegistry = registry.category("actions");
import { _t } from "@web/core/l10n/translation";

class CustomDashBoard extends owl.Component {
    setup() {
        this.orm = useService('orm')
        this.action = useService('action')
        this.rootRef = useRef('root')
        this.state = useState({
            start_date: '',
            end_date: '',
            period: 'month'
        });

        // When the component is about to start, fetch data in tiles
        onWillStart(async () => {
            var self = this;
            this.props.title = 'Dashboard';
            var total_count = this.orm.call('venue.booking', 'get_total_booking')
                .then(function (result) {
                    self.props.booking_count = result.total_booking
                    self.props.total_venue = result.total_venue
                    self.props.total_amount = result.total_amount
                    self.props.total_invoice = result.total_invoice
                })
            var table_content = this.orm.call('venue.booking', 'get_top_venue')
                .then(function (result) {
                    self.props.upcoming = result.upcoming
                    self.props.venue = result.venue
                    self.props.customer = result.customer
                })
            return Promise.all([total_count, table_content]);
        });
        // When the component is mounted, render various charts
        onMounted(async () => {
            this.render_booking();
            this.render_venue();
            this.render_booking_status();
            // Apply default month filter
            this.on_change_booking_values({ target: { value: 'month' }, stopPropagation: () => {} });
        });
    };

    toggleFilterPopup() {
        $('#filter_popup').toggleClass('d-none');
    }

    get period_value() {
        const periods = {
            day: "Today",
            week: "This week",
            month: "This month",
            last_month: "Last month",
            year: "This year",
            last_year: "Last year",
            custom: "Custom"
        };

        return periods[this.state.period]
    }

    _get_dates_for_period(period) {
        const today = new Date();
        let start = new Date();
        let end = new Date();

        if (period === 'day') {
            start = today;
            end = today;
        } else if (period === 'week') {
            const day = today.getDay();
            const diff = today.getDate() - day + (day === 0 ? -6 : 1);
            start = new Date(new Date().setDate(diff));
            end = new Date(new Date().setDate(diff + 6));
        } else if (period === 'month') {
            start = new Date(today.getFullYear(), today.getMonth(), 1);
            end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        } else if (period === 'last_month') {
            start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
            end = new Date(today.getFullYear(), today.getMonth(), 0);
        } else if (period === 'year') {
            start = new Date(today.getFullYear(), 0, 1);
            end = new Date(today.getFullYear(), 11, 31);
        } else if (period === 'last_year') {
            start = new Date(today.getFullYear() - 1, 0, 1);
            end = new Date(today.getFullYear() - 1, 11, 31);
        } else {
            return { start: '', end: '' };
        }

        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        return { start: formatDate(start), end: formatDate(end) };
    }

    on_change_custom_date() {
        if (this.state.start_date && this.state.end_date) {
            this.state.period = 'custom';
            this.update_dashboard();
        }
    }

    update_dashboard() {
        var self = this;
        this.orm.call('venue.booking', 'get_select_filter', [this.state.period, this.state.start_date, this.state.end_date])
            .then(function (result) {
                self._update_stats(result, self.state.period);
                self.render_booking(self.state.start_date, self.state.end_date);
                self.render_venue(self.state.start_date, self.state.end_date);
                self.render_booking_status(self.state.start_date, self.state.end_date);
            });
    }

    on_click_bookings() {
        this.action.doAction({
            name: _t('All Bookings'),
            type: 'ir.actions.act_window',
            res_model: 'venue.booking',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    on_click_venues() {
        this.action.doAction({
            name: _t('All Venues'),
            type: 'ir.actions.act_window',
            res_model: 'venue',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    on_click_confirmed_bookings() {
        this.action.doAction({
            name: _t('Confirmed Bookings'),
            type: 'ir.actions.act_window',
            res_model: 'venue.booking',
            domain: [['state', 'in', ['confirm', 'invoice']]],
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    on_click_invoiced_bookings() {
        this.action.doAction({
            name: _t('Invoiced Bookings'),
            type: 'ir.actions.act_window',
            res_model: 'venue.booking',
            domain: [['state', '=', 'invoice']],
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    //Function for render booking graph
    render_booking(start_date = null, end_date = null) {
        var self = this
        var ctx = $("#booking");
        if (this.bookingChart) {
            this.bookingChart.destroy();
        }
        this.orm.call('venue.booking', 'get_select_filter', [this.state.period, start_date, end_date])
            .then(function (result) {
                var data = {
                    labels: result.cust_invoice_name,
                    datasets: [{
                        label: 'Invoice Sum',
                        data: result.cust_invoice_sum,
                        backgroundColor: [
                            "#003f5c", "#2f4b7c", "#f95d6a", "#665191", "#d45087",
                            "#ff7c43", "#ffa600", "#a05195", "#6d5c16"
                        ],
                        barPercentage: 0.5,
                        barThickness: 6,
                        maxBarThickness: 8,
                        minBarLength: 0,
                        borderWidth: 1,
                        fill: false
                    }]
                };
                var options = {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true }
                    },
                };
                self.bookingChart = new Chart(ctx, {
                    type: "bar",
                    data: data,
                    options: options
                });
            });
    }
    //Function for render venue graph
    render_venue(start_date = null, end_date = null) {
        var self = this
        var ctx = $("#venue");
        if (this.venueChart) {
            this.venueChart.destroy();
        }
        this.orm.call('venue.booking', 'get_select_filter', [this.state.period, start_date, end_date])
            .then(function (result) {
                var data = {
                    labels: result.truck_invoice_name,
                    datasets: [{
                        label: 'Total Sum',
                        data: result.truck_invoice_sum,
                        backgroundColor: [
                            "#665191", "#ff7c43", "#ffa600", "#d45087", "#a05195",
                            "#6d5c16", "#CCCCFF", "#003f5c", "#2f4b7c", "#f95d6a",
                        ],
                        borderWidth: 1,
                    }]
                };
                self.venueChart = new Chart(ctx, {
                    type: "pie",
                    data: data,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                    }
                });
            });
    }

    render_booking_status(start_date = null, end_date = null) {
        var self = this;
        var ctx = $("#booking_status_chart");
        if (this.statusChart) {
            this.statusChart.destroy();
        }
        this.orm.call('venue.booking', 'get_select_filter', [this.state.period, start_date, end_date])
            .then(function (result) {
                var data = {
                    labels: result.state_names,
                    datasets: [{
                        label: 'Bookings',
                        data: result.state_counts,
                        backgroundColor: [
                            "#4BC0C0", "#FF6384", "#36A2EB", "#FFCE56", "#9966FF"
                        ],
                        borderWidth: 1,
                    }]
                };
                self.statusChart = new Chart(ctx, {
                    type: "doughnut",
                    data: data,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                    }
                });
            });
    }

    //Function for filter the dashboard content
    on_change_booking_values(e) {
        if (e.stopPropagation) e.stopPropagation();
        const value = e.target.value;
        const dates = this._get_dates_for_period(value);
        this.state.period = value;
        this.state.start_date = dates.start;
        this.state.end_date = dates.end;
        this.update_dashboard();
    }

    _hide_all_stats() {
        $('.total').hide();
        $('#booking_this_year, #venue_this_year, #amount_this_year, #invoice_this_year').hide();
        $('#booking_this_last_year, #venue_this_last_year, #amount_this_last_year, #invoice_this_last_year').hide();
        $('#booking_this_day, #venue_this_day, #amount_this_day, #invoice_this_day').hide();
        $('#booking_this_week, #venue_this_week, #amount_this_week, #invoice_this_week').hide();
        $('#booking_this_month, #venue_this_month, #amount_this_month, #invoice_this_month').hide();
        $('#booking_this_last_month, #venue_this_last_month, #amount_this_last_month, #invoice_this_last_month').hide();
        $('#booking_this_dynamic, #venue_this_dynamic, #amount_this_dynamic, #invoice_this_dynamic').hide();
        $('#booking_this_custom, #venue_this_custom, #amount_this_custom, #invoice_this_custom').hide();
    }

    _update_stats(result, period) {
        this._hide_all_stats();
        var b_id = '#booking_this_' + period;
        var v_id = '#venue_this_' + period;
        var a_id = '#amount_this_' + period;
        var i_id = '#invoice_this_' + period;

        $(b_id + ',' + v_id + ',' + a_id + ',' + i_id).show().empty();
        $(b_id).append('<span>' + result['booking'][0]['count'] + '</span>');
        $(v_id).append('<span>' + result['venue_count'][0]['count'] + '</span>');
        $(a_id).append('<span>' + (result['amount'][0].sum || 0) + '</span>');
        $(i_id).append('<span>' + (result['invoice'][0].sum || 0) + '</span>');
    }

}
CustomDashBoard.template = "CustomDashBoard";
actionRegistry.add('dashboard_tags', CustomDashBoard);
