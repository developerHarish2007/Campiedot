import type { WorkOrderState } from '../contracts';
export type ApiNodeStatus='normal'|'incident'|'blocked'|'non-operational';
export const nodeStatusStyle:Record<ApiNodeStatus,{color:string;label:string}>={normal:{color:'#72c8a0',label:'Normal'},incident:{color:'#f2a84b',label:'Incident'},blocked:{color:'#df705e',label:'Blocked'},'non-operational':{color:'#a95757',label:'Non-operational'}};
export const workOrderLabel:Record<WorkOrderState,string>={OPEN:'Open',ASSIGNED:'Assigned',IN_PROGRESS:'In progress',COMPLETED:'Completed',BLOCKED:'Blocked'};
export const workOrderColor:Record<WorkOrderState,string>={OPEN:'#90a0ae',ASSIGNED:'#71a9dc',IN_PROGRESS:'#e7a04e',COMPLETED:'#72c8a0',BLOCKED:'#df705e'};
