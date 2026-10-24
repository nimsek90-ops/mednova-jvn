import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../static/js/video.js',import.meta.url),'utf8');
function harness(getUserMedia){
 const nodes=new Map();
 function node(id){if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',disabled:false,srcObject:null,addEventListener(){},setAttribute(){},querySelectorAll(){return []},append(){}});return nodes.get(id);}
 node('call-data').textContent=JSON.stringify({signal_url:'/synthetic/signals/',config:{},is_doctor:false});
 const context=vm.createContext({document:{getElementById:node,querySelector:()=>({value:'synthetic-csrf'}),createElement:()=>({})},
 navigator:{mediaDevices:{getUserMedia,enumerateDevices:async()=>[]}},
 window:{RTCPeerConnection:function(){},addEventListener(){}},AbortController,
 RTCPeerConnection:class {addTrack(){} close(){}},
 fetch:async()=>({ok:true,json:async()=>({signals:[]})}),setTimeout:()=>1,clearTimeout(){}});
 vm.runInContext(source,context);return {context,node};
}
test('ending during pending media permission stops the late stream',async()=>{
 let resolve;let stopped=0;
 const h=harness(()=>new Promise(done=>resolve=done));
 const pending=vm.runInContext('start()',h.context);
 vm.runInContext('stop(false)',h.context);
 resolve({getTracks:()=>[{stop(){stopped++}}]});await pending;
 assert.equal(stopped,1);assert.equal(h.node('local-video').srcObject,null);
 assert.equal(vm.runInContext('active',h.context),false);
});
test('denied media permission restores controls with understandable feedback',async()=>{
 const h=harness(async()=>{const e=new Error('denied');e.name='NotAllowedError';throw e;});
 await vm.runInContext('start()',h.context);
 assert.equal(h.node('start-call').disabled,false);
 assert.match(h.node('call-status').textContent,/permission denied/);
 assert.equal(vm.runInContext('active',h.context),false);
});
