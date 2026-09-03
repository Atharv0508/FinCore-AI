export const API=import.meta.env.VITE_API_URL||'/api'
export async function api(path,options={}){let response;try{response=await fetch(API+path,{credentials:'include',headers:{'Content-Type':'application/json',...(options.headers||{})},...options})}catch(error){throw Error(`Cannot reach FinCore API at ${API}. Confirm the backend is running, then refresh this page.`)}const body=await response.json().catch(()=>({}));if(!response.ok)throw Error(body.detail||`Request failed (${response.status})`);return body}
export const rupees=value=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format((value||0)/100)
export const count=value=>new Intl.NumberFormat('en-IN').format(value||0)
