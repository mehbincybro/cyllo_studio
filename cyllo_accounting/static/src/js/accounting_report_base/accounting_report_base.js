/** @odoo-module **/
import { Component, onWillStart, useState, onWillUnmount, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ReportDropdown } from "./reportDropdown";
import { AnnotateDialog } from "./annotate_dialog";
import { download } from "@web/core/network/download";
import { useSaveContext } from "../hooks/useSaveContext";
import { useResize } from "@cyllo_base/js/hooks"
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";

const getValueFromLocalStorage = (key) => {
    const value = localStorage.getItem(key);
    if (value !== null) {
        try {
            return JSON.parse(value);
        } catch (e) {
            console.error(`Error parsing JSON for key: ${key}`, e);
            return false;
        }
    } else {
        console.warn(`No value found in localStorage for key: ${key}`);
        return false;
    }
}

const TIMEFRAMES = {
    'month': 'This Month',
    'quarter': 'This Quarter',
    'year': 'This Financial Year',
    'month_l': 'Last Month',
    'quarter_l': 'Last Quarter',
    'year_l': 'Last Financial Year',
    'custom': 'Custom'
}

const REPORTS = [
    "Partner Ledger",
    "General Ledger",
    "Aged Receivable",
    "Aged Payable"
]

export class AccountingReportBase extends Component {
    model = ""
    defaultDateFilter = 'month'
    pdfReport = true;
    ledgerId = 0
    breadCrumbs = false
    sidebarClass = {
        off: "",
        on: "",
        bodyOn:"",
        bodyOff: "",
    }

    setup() {
        this.env.bus.addEventListener("SIDEBAR_MENU_TOGGLE", ({ detail }) => {
            this.uiState.isSideBarActive = !detail.isSidebarOn
        })

        this.uiState = useState({
            isSideBarActive: true
        })
        this.orm = useService('orm');
        this.action = useService('action');
        this.ui = useService('ui');
        this.dialog = useService("dialog");
        this.company = useService("company");
        this.dialogService = useService("dialog");
        this.financialYear = {
            start_date: "",
            end_date: ""
        }
        this.filters = useState({
            dateFilterValue: this.defaultDateFilter,
            startDate: "",
            endDate: ""
        })
        this.searchViewId = false
        this.saveContext = useSaveContext()
        onWillStart(async () => {
            this.searchViewId = await this.orm.call("abstract.financial.report", "get_search_view", [])
        })
        onWillStart(this.setInitialValues)
        for (const report of REPORTS) { // Removes the opened lines if a new report is opened
            if (report !== this.reportName) {
                this.saveContext.removeManually(report)
            }
        }
    }

    get reportName() {
        return this.props.action.display_name || ''
    }

    get timeFrame() {
        return TIMEFRAMES
    }

    get dateFilterValue() {
        return this.timeFrame[this.filters.dateFilterValue]
    }

    get filterContext() {
        return {}
    }

    get args() {
        return []
    }

    get pdfData() {
        return ["", "", {}]
    }

    get xlsxData() {
        return ["", {}]
    }

    get periodData() {
        const { comparison, comparisonType } = this.state
        const { dateFilterValue } = this.filters
        const { start_date, end_date } = this.financialYear
        const periodData = []
        const today = new Date()
        if (comparison > 1) {
            for (let i = 0; i < comparison; i++) {
                if (comparisonType === "year") {
                    const formatedStartDate = moment(start_date).subtract(i, 'year').format('YYYY')
                    const formatedEndDate = moment(end_date).subtract(i, 'year').format('YYYY')
                    periodData.push(`${formatedStartDate} - ${formatedEndDate}`)
                } else {
                    const formatedMonth = moment(today).subtract(i, 'month').format('MMM YYYY')
                    periodData.push(formatedMonth)
                }
            }
        } else {
            const type = dateFilterValue.split('_')
            const { startDate, endDate } = this.filters
            const formatedStartDate = moment(startDate).format('YYYY')
            const formatedEndDate = moment(endDate).format('YYYY')
            switch (type[0]) {
                case "month":
                    periodData.push(`${moment(startDate).format('MMM YYYY')}`)
                    break;
                case "year":
                    periodData.push(`${formatedStartDate} - ${formatedEndDate}`)
                    break
                case "quarter":
                    const quarter = this.getQuarter(startDate); //Todo: [year1 - year2]  or [year - year] ??
                    periodData.push(`[Q${quarter}] ${formatedStartDate} - ${formatedEndDate}`)
                    break
                case "custom":
                    periodData.push(`[${startDate}] - [${endDate}]`)
                    break
            }
        }
        return periodData
    }

    getQuarter(date) {
        const adjustedDate = new Date(date);
        const financialYearStart = new Date(this.financialYear.start_date)
        adjustedDate.setFullYear(financialYearStart.getFullYear());
        const quarters = [
            {
                start: new Date(financialYearStart.getFullYear(), financialYearStart.getMonth(), financialYearStart.getDate()),
                end: new Date(financialYearStart.getFullYear(), financialYearStart.getMonth() + 3, financialYearStart.getDate() - 1)
            },
            {
                start: new Date(financialYearStart.getFullYear(), financialYearStart.getMonth() + 3, financialYearStart.getDate()),
                end: new Date(financialYearStart.getFullYear(), financialYearStart.getMonth() + 6, financialYearStart.getDate() - 1)
            },
            {
                start: new Date(financialYearStart.getFullYear(), financialYearStart.getMonth() + 6, financialYearStart.getDate()),
                end: new Date(financialYearStart.getFullYear(), financialYearStart.getMonth() + 9, financialYearStart.getDate() - 1)
            },
            {
                start: new Date(financialYearStart.getFullYear(), financialYearStart.getMonth() + 9, financialYearStart.getDate()),
                end: new Date(financialYearStart.getFullYear() + 1, financialYearStart.getMonth(), financialYearStart.getDate() - 1)
            }
        ];
        for (let i = 0; i < quarters.length; i++) {
            if (adjustedDate.getMonth() >= quarters[i].start.getMonth() && adjustedDate.getMonth() <= quarters[i].end.getMonth()) {
                return i + 1;
            }
        }
        return -1; // Return -1 if the date is not within the financial year
    }

    async getReport() {
        return await this.orm.call(this.model, "get_report", [...this.args], this.filterContext)
    }

    onSelectTimeFrame(time, force = true) {
        this.filters.dateFilterValue = time
        this.setDate()
    }

    async setInitialValues() {
        this.financialYear = await this.orm.call("abstract.financial.report", "get_financial_year", [])
        this.setDate()
    }

    openAnnotation(moveLineId, message = "", account) {
        this.dialog.add(AnnotateDialog, {
            title: 'Annotate',
            message: message,
            onConfirm: async (result) => {
                await this.writeAnnotation(moveLineId, result, account)
            }
        });
    }

    async writeAnnotation(moveLineId, value, account) {
        await this.orm.call("account.move.line", "write_annotations", [moveLineId, this.ledgerId, value])
    }

    async removeAnnotation(moveLineId, account) {
        await this.orm.call("account.move.line", "remove_annotations", [moveLineId, this.ledgerId])
    }

    setDate() {
        const [startDate, endDate] = this.getDate()
        this.filters.startDate = startDate
        this.filters.endDate = endDate
    }

    getDate() {
        const { dateFilterValue } = this.filters
        const filter = dateFilterValue.split('_')
        let startDate, endDate
        if (['year', 'year_l'].includes(dateFilterValue)) {
            ({ start_date: startDate, end_date: endDate } = this.financialYear)
            if (dateFilterValue === 'year') {
                return [startDate, endDate]
            } else {
                const currentStartDate = moment(startDate);
                const previousStartDate = moment(currentStartDate).subtract(1, 'year').format('YYYY-MM-DD');
                const currentEndDate = moment(endDate);
                const previousEndDate = moment(currentEndDate).subtract(1, 'year').format('YYYY-MM-DD');
                return [previousStartDate, previousEndDate]
            }
        } else if (dateFilterValue === 'today') {
            let today = new Date()
            today = moment(today).format('YYYY-MM-DD')
            return [today, today]
        } else {
            const momentValue = !Boolean(filter.length > 1) ? moment() : moment().subtract(1, filter[0]);
            startDate = momentValue.startOf(filter[0]).format('YYYY-MM-DD');
            endDate = momentValue.endOf(filter[0]).format('YYYY-MM-DD');
            return [startDate, endDate]
        }
    }

    onDateChange(ev, type) {
        this.filters.dateFilterValue = 'custom'
        const value = ev.target.value
        if (!value) {
            this.dialogService.add(WarningDialog, {
                title: _t("Warning: Missing Date"),
                message: _t("Please select a valid date before proceeding."),
            });
            return;
        }

        this.filters[type] = value;
    }

    printPDF() {
        const [report_name, report_file, data] = this.pdfData
        return this.action.doAction({
            type: 'ir.actions.report',
            report_type: 'qweb-pdf',
            report_name,
            report_file,
            data,
            display_name: this.reportName,
        })
    }

    async printXLSX() {
        const [model, xlsxData] = this.xlsxData
        const data = {
            model,
            data: JSON.stringify(xlsxData),
            output_format: 'xlsx',
            report_name: this.reportName,
        }
        this.ui.block()
        await download({
            url: '/cyllo_xlsx_report',
            data,
            complete: () => this.ui.unblock(),
            error: (error) => this.call('crash_manager', 'rpc_error', error),
        });
        this.ui.unblock()
    }

    onClickBreadCrumbs() {
        window.history.go(-1)
    }

    openGeneralLedger(accountId) {
        return this.action.doAction("cyllo_accounting.action_dynamic_general_ledger", {
            additionalContext: {
                accountId: accountId,
                breadCrumb: this.reportName
            },
        })
    }
}

AccountingReportBase.template = "AccountingReportBase"
AccountingReportBase.components = { Dropdown, DropdownItem, ReportDropdown }
