import {api} from './client.js';
export const datasets={list:()=>api('/datasets'),get:id=>api('/datasets/'+id),create:data=>api('/datasets',{method:'POST',body:JSON.stringify(data)}),grants:id=>api('/datasets/'+id+'/grants'),grant:(id,user_id)=>api('/datasets/'+id+'/grants',{method:'POST',body:JSON.stringify({user_id})}),revoke:(id,user_id)=>api('/datasets/'+id+'/grants/'+user_id,{method:'DELETE'}),scope:(id,visibility)=>api('/datasets/'+id+'/scope',{method:'POST',body:JSON.stringify({visibility})})};
export const jobs={list:()=>api('/jobs'),get:id=>api('/jobs/'+id),create:data=>api('/jobs',{method:'POST',body:JSON.stringify(data)}),approve:id=>api('/jobs/'+id+'/approve',{method:'POST'})};
export const reports={list:()=>api('/reports'),create:data=>api('/reports',{method:'POST',body:JSON.stringify(data)}),toggle:id=>api('/reports/'+id+'/toggle',{method:'POST'}),deliveries:()=>api('/deliveries')};
export const users={list:()=>api('/auth/users')};
