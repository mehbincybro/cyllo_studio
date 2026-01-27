/** @odoo-module **/

/**
 * SQLQueryParser class for parsing SQL queries and extracting relevant information.
 * @class
 */
export class SQLQueryParser {
    /**
     * Initializes the SQLQueryParser class with a given SQL query.
     * @constructor
     * @param {string} query - The SQL query to be parsed.
     */
    constructor(query) {
        this.query = query.replaceAll('public.', '');
    }

    /**
     * Parses the SQL query and extracts various components.
     * @function
     * @returns {Object} - An object containing information about joins, columns, where conditions,
     *                    group by columns, order by columns, and limit.
     */
    parse() {
        const tables = this.extractTables();
        this.query = this.query.replaceAll('*', `${tables[0].model}.id`)
        const columns = this.extractColumns();
        const where = this.extractWhereConditions();
        const groupBy = this.extractGroupByColumns();
        const orderBy = this.extractOrderBy();
        const limit = this.extractLimit();
        const joins = this.extractJoins();
        joins.forEach(item => tables.push(item))
        return {
            joins: tables,
            columns,
            where,
            groupBy,
            orderBy,
            limit,
        };
    }

    /**
     * Extracts the tables involved in the SQL query.
     * @function
     * @returns {Array} - An array of table information objects.
     */
    extractTables() {
        const regex_1 = /\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:AS\s+([a-zA-Z_][a-zA-Z0-9_]*))?\b/i;
        const regex_2 = /\bFROM\s+([a-zA-Z_][a-zA-Z0-9_])\s(?:AS\s+([a-zA-Z_][a-zA-Z0-9_]*))?\b/i;
        const regex_3 = /\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:AS\s+([a-zA-Z_][a-zA-Z0-9_]*))?(?:\s*->>'[a-zA-Z0-9_]+')?\b/i;

        var match = this.query.match(regex_1) || this.query.match(regex_2) || this.query.match(regex_3);
        if (match) {
            const model = match[1];
            const alias = match[2] || false;
            const join = alias ? `${model} AS ${alias}` : model
            return [{
                join,
                model,
                alias,
                name: false,
                linked: false,
                field: false
            }];
        }
    }

    /**
     * Extracts the columns selected in the SQL query.
     * @function
     * @returns {Array} - An array of column information objects.
     */
    extractColumns() {
        const regex = /SELECT\s+([^]+?)\s+FROM/i;
        const match = this.query.match(regex);
        if (match) {
            const columnStr = match[1];
            const columns = columnStr.split(',').map((column) => {
                let [name, alias] = column.trim().split(' AS ');
                let query = column.trim()
                if (!alias) {
                    alias = name.replaceAll('.', '_')
                    query = `${query} AS ${alias}`
                }
                return {
                    column: name,
                    alias,
                    query,
                    value: name.replace('.', ' > ')
                };
            });
            return columns;
        }
        return [];
    }

    /**
     * Extracts the WHERE conditions from the SQL query.
     * @function
     * @returns {Array} - An array of where condition objects.
     */
    extractWhereConditions() {
        const regex = /WHERE\s+([^]+?)(?:GROUP BY|ORDER BY|LIMIT|$)/i;
        const match = this.query.match(regex);
        if (match) {
            const conditions = match[1].trim().split(' AND ');
            const whereConditions = conditions.map((condition, index) => {
                return {
                    name: `Filter ${index + 1}`,
                    domain: ` ${condition}`,
                    active: true,
                    id: new Date().toISOString(), //temp Id
                    domain_py_expression: []
                };
            });
            return whereConditions;
        }
        return [];
    }

    /**
     * Extracts the GROUP BY columns from the SQL query.
     * @function
     * @returns {Array} - An array of group by column information objects.
     */
    extractGroupByColumns() {
        const regex = /GROUP BY\s+([^]+?)(?:ORDER BY|LIMIT|$)/i;
        const match = this.query.match(regex);
        if (match) {
            const columnStr = match[1];
            const columns = columnStr.split(',').map((column) => {
                const [name, alias] = column.trim().split(' AS ');
                return {
                    column: name,
                    alias: alias || false,
                    query: column.trim(),
                    value: name.replace('.', ' > ')
                };
            });
            return columns;
        }
        return [];
    }

    /**
     * Extracts the ORDER BY columns from the SQL query.
     * @function
     * @returns {Array} - An array of order by column information objects.
     */
    extractOrderBy() {
        const regex = /ORDER BY\s+([^]+?)(?:LIMIT|$)/i;
        const match = this.query.match(regex);
        if (match) {
            const columnStr = match[1];
            const columns = columnStr.split(',').map((column) => {
                const [name, alias] = column.trim().split(' AS ');
                const cleanName = name.replace(/\s+(DESC|ASC)$/i, '').trim(); // Remove DESC or ASC and trim
                return {
                    column: cleanName,
                    alias: alias || false,
                    query: column.trim(),
                    value: cleanName.replace('.', ' > ')
                };
            });
            return columns;
        }
        return [];
    }

    /**
     * Extracts the LIMIT value from the SQL query.
     * @function
     * @returns {number|null} - The limit value or null if not present.
     */
    extractLimit() {
        const regex = /LIMIT\s+(\d+)/i;
        const match = this.query.match(regex);
        return match ? parseInt(match[1]) : null;
    }

    /**
     * Extracts the JOIN clauses from the SQL query.
     * @function
     * @returns {Array} - An array of join information objects.
     */
    extractJoins() {
        const regex = /JOIN\s+([\w_]+)(?:\s+AS\s+([\w_]+))?\s+ON\s+([^]+?)(?=(?:JOIN|WHERE|GROUP BY|ORDER BY|LIMIT|$))/ig;
        const joins = [];
        let match;
        while ((match = regex.exec(this.query)) !== null) {
            const join = match[0].replace('\n', '').trim()
            const model = match[1];
            const alias = match[2] || false;
            const condition = match[3].trim();
            const linkedTableRegex = /([^\.]+)\.(\w+)\s*=\s*([^\.]+)\.(\w+)/;
            const linkedTableMatch = condition.match(linkedTableRegex);
            const linked = linkedTableMatch ? linkedTableMatch[3] : null;
            const field = linkedTableMatch ? linkedTableMatch[4] : null;

            joins.push({
                join,
                model,
                alias,
                linked,
                field,
                name: model.replaceAll('_', ' ')
            });
        }
        return joins;
    }
}
  