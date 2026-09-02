export const API=import.meta.env.VITE_API_URL||'http://localhost:8000'
export async function api(path,options={}){const response=await fetch(API+path,{credentials:'include',headers:{'Content-Type':'application/json',...(options.headers||{})},...options});const body=await response.json().catch(()=>({}));if(!response.ok)throw Error(body.detail||'Request failed');return body}
export const rupees=value=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format((value||0)/100)
