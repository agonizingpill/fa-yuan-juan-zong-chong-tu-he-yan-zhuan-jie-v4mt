import {store} from '../stores/workspace.js';import {esc} from '../utils/format.js';import {intakeStates} from '../constants/enums.js';import {badge} from './controls.js';
export const currentCase=()=>store.data.intakes.find(i=>i.id===store.selected);
export const caseOptions=()=>store.data.intakes.map(i=>`<option value="${i.id}" ${i.id===store.selected?'selected':''}>${esc(i.code)} · ${esc(i.alias)}</option>`).join('');
export function caseStrip(){const c=currentCase();const consent=store.data.consents.find(x=>x.intake_id===c.id);return `<section class="case-strip"><div><small>当前收件 / 事实版本 ${c.facts_version}</small><h2>${esc(c.code)} <span>${esc(c.alias)}</span></h2></div><div>${badge(intakeStates[c.status])}${badge(consent?.authorized?'转介授权有效':'授权未取得 / 已撤回',consent?.authorized?'good':'warning')}</div><p>${esc(c.facts)}</p></section>`;}
export function caseName(id){const c=store.data.intakes.find(i=>i.id===id);return c?esc(c.code)+' '+esc(c.alias):'未知卷宗';}
