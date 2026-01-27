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
    const codeArray = await this.orm.searchRead("node.struct", [["work_auto_id", "=", this.id]], ["code"])
    const {data} = this.editorValue[0]?.flow_data ? this.editorValue[0]?.flow_data?.drawflow?.Home : false
    const nodes = data ? Object.values(data) : []
    const contextNodes = nodes.map(node => {
        const isParent = node.name === "Condition";
        const code = codeArray.find(item => item.id === node.data.nodeId)?.code || ""
        return {
            nodeId: node.data.nodeId,
            parent: null,
            left: null,
            right: null,
            child1: isParent ? {left: null, right: null, code: "pass"} : null,
            child2: null,
            isParent,
            code
        }
    })

    contextNodes.forEach(node => {
        const dNode = nodes.find(item => item.data.nodeId === node.nodeId);
        if (dNode.outputs) {
            if (node.isParent) {
                const child1 = dNode.outputs?.output_1
                const child2 = dNode.outputs?.output_2
                const right = dNode.outputs?.output_3
                if (child1.connections.length > 0) {
                    const childId = child1.connections[0].node
                    const childNode = nodes.find(item => item.id == childId);
                    const ctxNode = contextNodes.find(item => item.nodeId == childNode.data.nodeId);
                    node.child1 = ctxNode
                }

                if (child2.connections?.length > 0) {
                    const childId = child2.connections[0].node
                    const childNode = nodes.find(item => item.id == childId);
                    const ctxNode = contextNodes.find(item => item.nodeId == childNode.data.nodeId);
                    node.child2 = ctxNode
                }
                if (right.connections.length > 0) {
                    const childId = right.connections[0].node
                    const childNode = nodes.find(item => item.id == childId);
                    const ctxNode = contextNodes.find(item => item.nodeId == childNode.data.nodeId);
                    node.right = ctxNode
                }
            } else {
                if (dNode.outputs.output_1?.connections?.length > 0) {
                    const outputId = dNode.outputs.output_1.connections[0].node
                    const outPutNode = nodes.find(item => item.id == outputId);
                    const outPutNodeCtx = contextNodes.find((item => item.nodeId === outPutNode.data.nodeId));
                    node.right = outPutNodeCtx
                }
            }
        }

        if (dNode.inputs?.input_1?.connections?.length > 0) {
            const inputId = dNode.inputs.input_1.connections[0].node
            const inPutNode = nodes.find(item => item.id == inputId);
            const inPutNodeCtx = contextNodes.find((item => item.nodeId === inPutNode.data.nodeId));
            node.left = inPutNodeCtx
        }
    })
    this.env.context.setContext({nodes: [...contextNodes]})
}