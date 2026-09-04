export const API=import.meta.env.VITE_API_URL||'/api'
function describeDetail(detail){
  if(typeof detail==='string') return detail
  if(Array.isArray(detail)) return detail.map(e=>typeof e==='string'?e:(e?.msg||JSON.stringify(e))).join('; ')
  if(detail&&typeof detail==='object') return detail.msg||JSON.stringify(detail)
  return null
}
export async function api(path,options={}){let response;try{response=await fetch(API+path,{credentials:'include',headers:{'Content-Type':'application/json',...(options.headers||{})},...options})}catch(error){throw Error(`Cannot reach FinCore API at ${API}. Confirm the backend is running, then refresh this page.`)}const text=await response.text();let body={};try{body=text?JSON.parse(text):{}}catch(error){}if(!response.ok){const detail=describeDetail(body.detail)||text.trim();throw Error(detail||`Request failed (${response.status}) at ${path}`)}return body}
export const rupees=value=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format((value||0)/100)
export const count=value=>new Intl.NumberFormat('en-IN').format(value||0)