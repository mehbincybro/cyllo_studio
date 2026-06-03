/** @odoo-module */

export function removeNodeIdFromVariables(contextVariables, nodeId) {
    contextVariables.forEach(variable => {
        if (variable && variable.usedIn) {
            const index = variable.usedIn.indexOf(nodeId);
            if (index !== -1) {
                variable.usedIn.splice(index, 1);
            }
        }
    });
}

export async function settingInitialContext() {
    // else_setup_code is only set on cron-mode Condition nodes; it carries
    // the complement recordset search line that the code engine injects at
    // the start of the ELSE block so both branches execute independently.
    const codeArray = await this.orm.searchRead("node.struct", [["work_auto_id", "=", this.id]], ["code", "else_setup_code"])

    // Guard: flow_data may be null on a brand-new workflow (no nodes saved yet).
    const homeData = this.editorValue[0]?.flow_data?.drawflow?.Home;
    const data = homeData?.data || null;
    const nodes = data ? Object.values(data) : [];

    const contextNodes = nodes.map(node => {
        const isParent = node.name === "Condition" || node.name === "Loop" || node.name === "TryCatch";
        const isTryCatch = node.name === "TryCatch";
        const isLoop = node.name === "Loop";
        const nodeStruct = codeArray.find(item => item.id === node.data.nodeId);
        const code = nodeStruct?.code || ""
        const else_setup_code = nodeStruct?.else_setup_code || null;
        const type = nodeStruct?.type || node.data.type || "node";
        const trigger_type = nodeStruct?.trigger_type || node.data.trigger_type || null;
        const ttype = nodeStruct?.ttype || node.data.ttype || null;
        return {
            nodeId: node.data.nodeId,
            parent: null,
            left: null,
            right: null,
            child1: isParent ? { left: null, right: null, code: "pass" } : null,
            child2: null,
            isParent,
            isTryCatch,
            isLoop,
            code,
            else_setup_code,
            type,
            trigger_type,
            ttype,
        }
    })


    contextNodes.forEach(node => {
        const dNode = nodes.find(item => item.data.nodeId === node.nodeId);
        if (dNode.outputs) {
            Object.entries(dNode.outputs).forEach(([outputName, output]) => {
                const connections = output.connections || [];
                if (connections.length > 0) {
                    const outputIdx = outputName.split('_')[1];
                    let propName = 'right';
                    if (node.isParent) {
                        propName = outputIdx === '3' ? 'right' : `child${outputIdx}`;
                    }

                    const targets = connections.map(conn => {
                        const targetDNode = nodes.find(item => item.id == conn.node);
                        return targetDNode ? contextNodes.find(item => item.nodeId === targetDNode.data.nodeId) : null;
                    }).filter(Boolean);

                    if (targets.length > 0) {
                        node[propName] = targets.length === 1 ? targets[0] : targets;
                    }
                }
            });
        }

        if (dNode.inputs?.input_1?.connections?.length > 0) {
            const inputId = dNode.inputs.input_1.connections[0].node
            const inPutNode = nodes.find(item => item.id == inputId);
            if (inPutNode) {
                const inPutNodeCtx = contextNodes.find((item => item.nodeId === inPutNode.data.nodeId));
                node.left = inPutNodeCtx || null;
            }
        }
    })
    this.env.context.setContext({ nodes: [...contextNodes] })
}