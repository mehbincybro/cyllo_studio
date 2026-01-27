/** @odoo-module **/

export class ThemeMaker {
    /**
     * Class for creating a theme for the Cyllo dashboard.
     * @param {object} theme - The theme data including colors and styles.
     */
    constructor(theme){
        this.theme = theme
    }
    /**
     * Initialize the theme by applying the specified colors and styles to the dashboard.
     * @returns {object} - The theme data with style information.
     */
    initTheme(){
        var theme = this.theme
        var root = document.querySelector(':root');
        var primary_color = theme.theme_color_ids ? theme.theme_color_ids[0] : "#000"
        root.style.setProperty('--dashboard-text-color', theme.title || "#000");
        root.style.setProperty('--dashboard-primary-color', primary_color);
        root.style.setProperty('--dashboard-background-color', theme.background || "#fff");
        let modalColor = theme.background === 'rgba(0,0,0,0)' ? 'rgba(255,255,255,1)': theme.background?.replace(/(rgba\(.+),\s*[^)]+\)/, '$1,1)') || 'rgba(255,255,255,1)';
        root.style.setProperty('--dashboard-modal-background-color', modalColor || "#fff");

        return {
            "themeName": theme.name,
            "seriesCnt": 4,
            "backgroundColor": theme.background,
            "title": {
                "textStyle": {
                    "color": theme.title
                },
                "subtextStyle": {
                    "color": theme.subtitle
                }
            },
            "textColorShow": false,
            "textColor": theme.label_text,
            "markTextColor": "#eee",
            "color": theme.theme_color_ids,
            graph: {
                color: theme.theme_color_ids,
                "itemStyle": {
                  "borderWidth": theme.border_width,
                  "borderColor": theme.border_color
                },
            },
            "legend": {
                "textStyle": {
                    "color": theme.subtitle
                }
            },
        }
    }
    /**
     * Get the theme and register it in ECharts to apply it to the dashboard.
     * @returns {string} - The name Banner 2of the registered theme.
     */
    getTheme(){
        var theme = this.initTheme()
        echarts.registerTheme(theme.themeName, theme)
        return theme.themeName
    }
}