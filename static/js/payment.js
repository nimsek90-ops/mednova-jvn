'use strict';
const config=JSON.parse(document.getElementById('payment-data').textContent),output=document.getElementById('payment-status');
document.getElementById('start-payment').addEventListener('click',()=>{
 if(typeof Razorpay==='undefined'){output.textContent='Payment provider unavailable. Please try again later.';return;}
 const checkout=new Razorpay({...config,handler:async result=>{output.textContent='Verifying payment. Please wait.';try{const r=await fetch(config.verify_url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':document.querySelector('#payment-token input').value},body:JSON.stringify(result)});const body=await r.json();output.textContent=r.ok?'Payment confirmed. Return to the appointment.':body.error;}catch{output.textContent='Verification could not complete. Contact the hospital if money was debited.';}},modal:{ondismiss:()=>{output.textContent='Checkout closed.';}}});
 checkout.on('payment.failed',()=>{output.textContent='Payment failed. Retry or contact the hospital.';});checkout.open();
});
