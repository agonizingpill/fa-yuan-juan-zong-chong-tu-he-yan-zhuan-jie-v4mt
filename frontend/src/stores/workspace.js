import {request} from '../api/client.js';
export const store={data:{},selected:Number(localStorage.getItem('aid-selected')||2),session:JSON.parse(localStorage.getItem('aid-session')||'null')};
export async function reload(){store.data=await request('/workspace');if(!store.data.intakes.some(i=>i.id===store.selected))store.selected=store.data.intakes[0]?.id;return store.data;}
export async function login(username,password){store.session=await request('/auth/login',{username,password});localStorage.setItem('aid-session',JSON.stringify(store.session));}
export function selectCase(id){store.selected=+id;localStorage.setItem('aid-selected',id);}
export function logout(){localStorage.removeItem('aid-session');location.reload();}
