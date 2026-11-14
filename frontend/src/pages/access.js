import {datasets,users} from '../api/entities.js';
import {workspace} from '../stores/workspace.js';
import {heading} from '../components/common/shell.js';
import {Role,Visibility} from '../constants/enums.js';
import {esc,date,notify} from '../utils/dom.js';
export async function accessPage(){
 const [list,accounts]=await Promise.all([datasets.list(),users.list()]);
 workspace.datasets=list;workspace.accounts=accounts;
 const selectedId=workspace.selectedDataset&&list.some(d=>d.id===workspace.selectedDataset)?workspace.selectedDataset:(list[0]&&list[0].id);
 let detail=null;
 if(selectedId){detail=await datasets.grants(selectedId);workspace.selectedDataset=selectedId;}
 const d=detail?detail.dataset:null;
 const grantedIds=new Set((detail?.grants||[]).map(g=>g.user_id));
 const candidates=accounts.filter(a=>a.role!=='admin'&&!grantedIds.has(a.id));
 const userName=id=>{const a=accounts.find(x=>x.id===id);return a?esc(a.name)+'（'+esc(a.email)+'）':'账号 #'+id;};
 return heading('06 / ACCESS CONTROL','批次授权与共享范围','复盘包含未公开事故：负责人按批次授权指定账号，分析结果与归档继承相同隔离。撤权立即取消该账号未完成的分析。')+
 '<div class="access-grid"><section class="panel"><div class="section-title"><h2>选择批次</h2><span>'+list.length+' 批</span></div><div class="batch-list">'+list.map(x=>'<button class="batch-item'+(d&&x.id===d.id?' active':'')+'" data-access-dataset="'+x.id+'"><strong>'+esc(x.name)+'</strong><span>'+(Visibility[x.visibility]||x.visibility)+(x.scope_confirmed?'':' · 待确认')+'</span></button>').join('')+'</div></section>'+
 (d?'<section class="panel"><div class="section-title"><h2>'+esc(d.name)+'</h2><span class="scope-badge '+(d.scope_confirmed?'':'pending')+'">'+(Visibility[d.visibility]||d.visibility)+(d.scope_confirmed?'':' · 共享范围待确认')+'</span></div>'+
 '<p class="hint">'+(d.scope_confirmed?'当前范围已确认生效。':'该批次来自既有数据，暂保持全部账号可读；确认后按所选范围立即生效。')+'</p>'+
 '<div class="scope-actions"><button class="button small" data-scope="private">确认为私有（仅授权账号）</button><button class="button small" data-scope="shared">确认为共享（全部账号）</button></div>'+
 '<div class="section-title"><h2>已授权账号</h2><span>'+detail.grants.length+' 个</span></div>'+
 (detail.grants.length?detail.grants.map(g=>'<div class="grant-row"><div><strong>'+esc(g.user?g.user.name:'账号 #'+g.user_id)+'</strong><p>'+esc(g.user?g.user.email:'')+' · '+esc(Role[g.user?g.user.role:'']||'')+'</p><small>'+esc(g.granted_by)+' 授权 · '+date(g.created_at)+'</small></div><button class="button small" data-revoke="'+g.user_id+'">撤销</button></div>').join(''):'<p class="empty">尚无授权账号。私有批次仅负责人可见。</p>')+
 '<form id="grant-form"><label>添加授权账号<select name="user_id" required>'+candidates.map(a=>'<option value="'+a.id+'">'+esc(a.name)+' · '+esc(a.email)+' · '+esc(Role[a.role]||a.role)+'</option>').join('')+'</select></label><button type="submit" class="primary" '+(candidates.length?'':'disabled')+'>授权该账号</button></form>'+
 '<div class="section-title"><h2>已取消的分析任务</h2><span>'+detail.cancelled_jobs.length+' 条</span></div>'+
 (detail.cancelled_jobs.length?detail.cancelled_jobs.map(j=>'<div class="grant-row cancelled"><div><strong>'+esc(j.name)+'</strong><p>'+userName(j.created_by)+'</p><small>'+esc(j.cancel_reason)+' · '+date(j.finished_at)+'</small></div></div>').join(''):'<p class="empty">没有因撤权取消的任务。</p>')+
 '</section>':'<section class="panel empty">暂无数据批次。</section>')+'</div>';
}
export function bindAccess(refresh){
 document.querySelectorAll('[data-access-dataset]').forEach(b=>b.onclick=async()=>{workspace.selectedDataset=Number(b.dataset.accessDataset);await refresh();});
 document.querySelectorAll('[data-scope]').forEach(b=>b.onclick=async()=>{try{const r=await datasets.scope(workspace.selectedDataset,b.dataset.scope);notify('共享范围已确认为'+(Visibility[r.visibility]||r.visibility)+'并生效');await refresh();}catch(e){notify(e.message,true);}});
 document.querySelectorAll('[data-revoke]').forEach(b=>b.onclick=async()=>{try{const r=await datasets.revoke(workspace.selectedDataset,Number(b.dataset.revoke));notify('已撤销授权'+(r.cancelled_jobs.length?'，取消 '+r.cancelled_jobs.length+' 个未完成任务':''));await refresh();}catch(e){notify(e.message,true);}});
 const form=document.querySelector('#grant-form');
 if(form)form.addEventListener('submit',async e=>{e.preventDefault();try{await datasets.grant(workspace.selectedDataset,Number(new FormData(form).get('user_id')));notify('已授权');await refresh();}catch(error){notify(error.message,true);}});
}
