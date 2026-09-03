export const API=import.meta.env.VITE_API_URL||'/api'
export async function api(path,options={}){let response;try{response=await fetch(API+path,{credentials:'include',headers:{'Content-Type':'application/json',...(options.headers||{})},...options})}catch(error){throw Error(`Cannot reach FinCore API at ${API}. Confirm the backend is running, then refresh this page.`)}const text=await response.text();let body={};try{body=text?JSON.parse(text):{}}catch(error){}if(!response.ok){const detail=body.detail||text.trim();throw Error(detail||`Request failed (${response.status}) at ${path}`)}return body}
export const rupees=value=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format((value||0)/100)
export const count=value=>new Intl.NumberFormat('en-IN').format(value||0)
