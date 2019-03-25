# -*- coding: utf-8 -*-
"""
    sphinx.search.pt
    ~~~~~~~~~~~~~~~~

    Portuguese search language: includes the JS Portuguese stemmer.

    :copyright: Copyright 2007-2013 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from sphinx.search import SearchLanguage, parse_stop_word

import snowballstemmer

if False:
    # For type annotation
    from typing import Any  # NOQA


portuguese_stopwords = parse_stop_word(u'''
| source: http://snowball.tartarus.org/algorithms/portuguese/stop.txt
de             |  of, from
a              |  the; to, at; her
o              |  the; him
que            |  who, that
e              |  and
do             |  de + o
da             |  de + a
em             |  in
um             |  a
para           |  for
  | é          from SER
com            |  with
não            |  not, no
uma            |  a
os             |  the; them
no             |  em + o
se             |  himself etc
na             |  em + a
por            |  for
mais           |  more
as             |  the; them
dos            |  de + os
como           |  as, like
mas            |  but
  | foi        from SER
ao             |  a + o
ele            |  he
das            |  de + as
  | tem        from TER
à              |  a + a
seu            |  his
sua            |  her
ou             |  or
  | ser        from SER
quando         |  when
muito          |  much
  | há         from HAV
nos            |  em + os; us
já             |  already, now
  | está       from EST
eu             |  I
também         |  also
só             |  only, just
pelo           |  per + o
pela           |  per + a
até            |  up to
isso           |  that
ela            |  he
entre          |  between
  | era        from SER
depois         |  after
sem            |  without
mesmo          |  same
aos            |  a + os
  | ter        from TER
seus           |  his
quem           |  whom
nas            |  em + as
me             |  me
esse           |  that
eles           |  they
  | estão      from EST
você           |  you
  | tinha      from TER
  | foram      from SER
essa           |  that
num            |  em + um
nem            |  nor
suas           |  her
meu            |  my
às             |  a + as
minha          |  my
  | têm        from TER
numa           |  em + uma
pelos          |  per + os
elas           |  they
  | havia      from HAV
  | seja       from SER
qual           |  which
  | será       from SER
nós            |  we
  | tenho      from TER
lhe            |  to him, her
deles          |  of them
essas          |  those
esses          |  those
pelas          |  per + as
este           |  this
  | fosse      from SER
dele           |  of him

 | other words. There are many contractions such as naquele = em+aquele,
 | mo = me+o, but they are rare.
 | Indefinite article plural forms are also rare.

tu             |  thou
te             |  thee
vocês          |  you (plural)
vos            |  you
lhes           |  to them
meus           |  my
minhas
teu            |  thy
tua
teus
tuas
nosso          | our
nossa
nossos
nossas

dela           |  of her
delas          |  of them

esta           |  this
estes          |  these
estas          |  these
aquele         |  that
aquela         |  that
aqueles        |  those
aquelas        |  those
isto           |  this
aquilo         |  that

               | forms of estar, to be (not including the infinitive):
estou
está
estamos
estão
estive
esteve
estivemos
estiveram
estava
estávamos
estavam
estivera
estivéramos
esteja
estejamos
estejam
estivesse
estivéssemos
estivessem
estiver
estivermos
estiverem

               | forms of haver, to have (not including the infinitive):
hei
há
havemos
hão
houve
houvemos
houveram
houvera
houvéramos
haja
hajamos
hajam
houvesse
houvéssemos
houvessem
houver
houvermos
houverem
houverei
houverá
houveremos
houverão
houveria
houveríamos
houveriam

               | forms of ser, to be (not including the infinitive):
sou
somos
são
era
éramos
eram
fui
foi
fomos
foram
fora
fôramos
seja
sejamos
sejam
fosse
fôssemos
fossem
for
formos
forem
serei
será
seremos
serão
seria
seríamos
seriam

               | forms of ter, to have (not including the infinitive):
tenho
tem
temos
tém
tinha
tínhamos
tinham
tive
teve
tivemos
tiveram
tivera
tivéramos
tenha
tenhamos
tenham
tivesse
tivéssemos
tivessem
tiver
tivermos
tiverem
terei
terá
teremos
terão
teria
teríamos
teriam
''')

js_stemmer = u"""

var JSX={};(function(j){function l(b,e){var a=function(){};a.prototype=e.prototype;var c=new a;for(var d in b){b[d].prototype=c}}function I(c,b){for(var a in b.prototype)if(b.prototype.hasOwnProperty(a))c.prototype[a]=b.prototype[a]}function h(a,b,d){function c(a,b,c){delete a[b];a[b]=c;return c}Object.defineProperty(a,b,{get:function(){return c(a,b,d())},set:function(d){c(a,b,d)},enumerable:true,configurable:true})}function J(a,b,c){return a[b]=a[b]/c|0}var p=parseInt;var z=parseFloat;function K(a){return a!==a}var x=isFinite;var w=encodeURIComponent;var u=decodeURIComponent;var t=encodeURI;var s=decodeURI;var A=Object.prototype.toString;var q=Object.prototype.hasOwnProperty;function k(){}j.require=function(b){var a=o[b];return a!==undefined?a:null};j.profilerIsRunning=function(){return k.getResults!=null};j.getProfileResults=function(){return(k.getResults||function(){return{}})()};j.postProfileResults=function(a,b){if(k.postResults==null)throw new Error('profiler has not been turned on');return k.postResults(a,b)};j.resetProfileResults=function(){if(k.resetResults==null)throw new Error('profiler has not been turned on');return k.resetResults()};j.DEBUG=false;function r(){};l([r],Error);function a(a,b,c){this.F=a.length;this.K=a;this.L=b;this.I=c;this.H=null;this.P=null};l([a],Object);function n(){};l([n],Object);function i(){var a;var b;var c;this.G={};a=this.E='';b=this._=0;c=this.A=a.length;this.D=0;this.B=b;this.C=c};l([i],n);function v(a,b){a.E=b.E;a._=b._;a.A=b.A;a.D=b.D;a.B=b.B;a.C=b.C};function f(b,d,c,e){var a;if(b._>=b.A){return false}a=b.E.charCodeAt(b._);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._++;return true};function g(a,d,c,e){var b;if(a._>=a.A){return false}b=a.E.charCodeAt(a._);if(b>e||b<c){a._++;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._++;return true}return false};function d(a,b,d){var c;if(a._-a.D<b){return false}if(a.E.slice((c=a._)-b,c)!==d){return false}a._-=b;return true};function m(f,m,p){var b;var d;var e;var n;var g;var k;var l;var i;var h;var c;var a;var j;var o;b=0;d=p;e=f._;n=f.A;g=0;k=0;l=false;while(true){i=b+(d-b>>>1);h=0;c=g<k?g:k;a=m[i];for(j=c;j<a.F;j++){if(e+c===n){h=-1;break}h=f.E.charCodeAt(e+c)-a.K.charCodeAt(j);if(h!==0){break}c++}if(h<0){d=i;k=c}else{b=i;g=c}if(d-b<=1){if(b>0){break}if(d===b){break}if(l){break}l=true}}while(true){a=m[b];if(g>=a.F){f._=e+a.F|0;if(a.H==null){return a.I}o=a.H(a.P);f._=e+a.F|0;if(o){return a.I}}b=a.L;if(b<0){return 0}}return-1};function e(d,m,p){var b;var g;var e;var n;var f;var k;var l;var i;var h;var c;var a;var j;var o;b=0;g=p;e=d._;n=d.D;f=0;k=0;l=false;while(true){i=b+(g-b>>1);h=0;c=f<k?f:k;a=m[i];for(j=a.F-1-c;j>=0;j--){if(e-c===n){h=-1;break}h=d.E.charCodeAt(e-1-c)-a.K.charCodeAt(j);if(h!==0){break}c++}if(h<0){g=i;k=c}else{b=i;f=c}if(g-b<=1){if(b>0){break}if(g===b){break}if(l){break}l=true}}while(true){a=m[b];if(f>=a.F){d._=e-a.F|0;if(a.H==null){return a.I}o=a.H(d);d._=e-a.F|0;if(o){return a.I}}b=a.L;if(b<0){return 0}}return-1};function B(a,b,d,e){var c;c=e.length-(d-b);a.E=a.E.slice(0,b)+e+a.E.slice(d);a.A+=c|0;if(a._>=d){a._+=c|0}else if(a._>b){a._=b}return c|0};function c(a,f){var b;var c;var d;var e;b=false;if((c=a.B)<0||c>(d=a.C)||d>(e=a.A)||e>a.E.length?false:true){B(a,a.B,a.C,f);b=true}return b};i.prototype.J=function(){return false};i.prototype.a=function(b){var a;var c;var d;var e;a=this.G['.'+b];if(a==null){c=this.E=b;d=this._=0;e=this.A=c.length;this.D=0;this.B=d;this.C=e;this.J();a=this.E;this.G['.'+b]=a}return a};i.prototype.stemWord=i.prototype.a;i.prototype.b=function(e){var d;var b;var c;var a;var f;var g;var h;d=[];for(b=0;b<e.length;b++){c=e[b];a=this.G['.'+c];if(a==null){f=this.E=c;g=this._=0;h=this.A=f.length;this.D=0;this.B=g;this.C=h;this.J();a=this.E;this.G['.'+c]=a}d.push(a)}return d};i.prototype.stemWords=i.prototype.b;function b(){i.call(this);this.I_p2=0;this.I_p1=0;this.I_pV=0};l([b],i);b.prototype.M=function(a){this.I_p2=a.I_p2;this.I_p1=a.I_p1;this.I_pV=a.I_pV;v(this,a)};b.prototype.copy_from=b.prototype.M;b.prototype.V=function(){var a;var e;var d;b:while(true){e=this._;d=true;a:while(d===true){d=false;this.B=this._;a=m(this,b.a_0,3);if(a===0){break a}this.C=this._;switch(a){case 0:break a;case 1:if(!c(this,'a~')){return false}break;case 2:if(!c(this,'o~')){return false}break;case 3:if(this._>=this.A){break a}this._++;break}continue b}this._=e;break b}return true};b.prototype.r_prelude=b.prototype.V;function E(a){var d;var f;var e;b:while(true){f=a._;e=true;a:while(e===true){e=false;a.B=a._;d=m(a,b.a_0,3);if(d===0){break a}a.C=a._;switch(d){case 0:break a;case 1:if(!c(a,'a~')){return false}break;case 2:if(!c(a,'o~')){return false}break;case 3:if(a._>=a.A){break a}a._++;break}continue b}a._=f;break b}return true};b.prototype.T=function(){var u;var w;var x;var y;var t;var l;var d;var e;var h;var i;var c;var j;var k;var a;var m;var n;var o;var p;var q;var r;var s;var v;this.I_pV=s=this.A;this.I_p1=s;this.I_p2=s;u=this._;l=true;a:while(l===true){l=false;d=true;g:while(d===true){d=false;w=this._;e=true;b:while(e===true){e=false;if(!f(this,b.g_v,97,250)){break b}h=true;f:while(h===true){h=false;x=this._;i=true;c:while(i===true){i=false;if(!g(this,b.g_v,97,250)){break c}d:while(true){c=true;e:while(c===true){c=false;if(!f(this,b.g_v,97,250)){break e}break d}if(this._>=this.A){break c}this._++}break f}this._=x;if(!f(this,b.g_v,97,250)){break b}c:while(true){j=true;d:while(j===true){j=false;if(!g(this,b.g_v,97,250)){break d}break c}if(this._>=this.A){break b}this._++}}break g}this._=w;if(!g(this,b.g_v,97,250)){break a}k=true;c:while(k===true){k=false;y=this._;a=true;b:while(a===true){a=false;if(!g(this,b.g_v,97,250)){break b}e:while(true){m=true;d:while(m===true){m=false;if(!f(this,b.g_v,97,250)){break d}break e}if(this._>=this.A){break b}this._++}break c}this._=y;if(!f(this,b.g_v,97,250)){break a}if(this._>=this.A){break a}this._++}}this.I_pV=this._}v=this._=u;t=v;n=true;a:while(n===true){n=false;b:while(true){o=true;c:while(o===true){o=false;if(!f(this,b.g_v,97,250)){break c}break b}if(this._>=this.A){break a}this._++}b:while(true){p=true;c:while(p===true){p=false;if(!g(this,b.g_v,97,250)){break c}break b}if(this._>=this.A){break a}this._++}this.I_p1=this._;b:while(true){q=true;c:while(q===true){q=false;if(!f(this,b.g_v,97,250)){break c}break b}if(this._>=this.A){break a}this._++}c:while(true){r=true;b:while(r===true){r=false;if(!g(this,b.g_v,97,250)){break b}break c}if(this._>=this.A){break a}this._++}this.I_p2=this._}this._=t;return true};b.prototype.r_mark_regions=b.prototype.T;function F(a){var x;var y;var z;var u;var v;var l;var d;var e;var h;var i;var j;var k;var c;var m;var n;var o;var p;var q;var r;var s;var t;var w;a.I_pV=t=a.A;a.I_p1=t;a.I_p2=t;x=a._;l=true;a:while(l===true){l=false;d=true;g:while(d===true){d=false;y=a._;e=true;b:while(e===true){e=false;if(!f(a,b.g_v,97,250)){break b}h=true;f:while(h===true){h=false;z=a._;i=true;c:while(i===true){i=false;if(!g(a,b.g_v,97,250)){break c}d:while(true){j=true;e:while(j===true){j=false;if(!f(a,b.g_v,97,250)){break e}break d}if(a._>=a.A){break c}a._++}break f}a._=z;if(!f(a,b.g_v,97,250)){break b}c:while(true){k=true;d:while(k===true){k=false;if(!g(a,b.g_v,97,250)){break d}break c}if(a._>=a.A){break b}a._++}}break g}a._=y;if(!g(a,b.g_v,97,250)){break a}c=true;c:while(c===true){c=false;u=a._;m=true;b:while(m===true){m=false;if(!g(a,b.g_v,97,250)){break b}e:while(true){n=true;d:while(n===true){n=false;if(!f(a,b.g_v,97,250)){break d}break e}if(a._>=a.A){break b}a._++}break c}a._=u;if(!f(a,b.g_v,97,250)){break a}if(a._>=a.A){break a}a._++}}a.I_pV=a._}w=a._=x;v=w;o=true;a:while(o===true){o=false;b:while(true){p=true;c:while(p===true){p=false;if(!f(a,b.g_v,97,250)){break c}break b}if(a._>=a.A){break a}a._++}b:while(true){q=true;c:while(q===true){q=false;if(!g(a,b.g_v,97,250)){break c}break b}if(a._>=a.A){break a}a._++}a.I_p1=a._;b:while(true){r=true;c:while(r===true){r=false;if(!f(a,b.g_v,97,250)){break c}break b}if(a._>=a.A){break a}a._++}c:while(true){s=true;b:while(s===true){s=false;if(!g(a,b.g_v,97,250)){break b}break c}if(a._>=a.A){break a}a._++}a.I_p2=a._}a._=v;return true};b.prototype.U=function(){var a;var e;var d;b:while(true){e=this._;d=true;a:while(d===true){d=false;this.B=this._;a=m(this,b.a_1,3);if(a===0){break a}this.C=this._;switch(a){case 0:break a;case 1:if(!c(this,'ã')){return false}break;case 2:if(!c(this,'õ')){return false}break;case 3:if(this._>=this.A){break a}this._++;break}continue b}this._=e;break b}return true};b.prototype.r_postlude=b.prototype.U;function G(a){var d;var f;var e;b:while(true){f=a._;e=true;a:while(e===true){e=false;a.B=a._;d=m(a,b.a_1,3);if(d===0){break a}a.C=a._;switch(d){case 0:break a;case 1:if(!c(a,'ã')){return false}break;case 2:if(!c(a,'õ')){return false}break;case 3:if(a._>=a.A){break a}a._++;break}continue b}a._=f;break b}return true};b.prototype.S=function(){return!(this.I_pV<=this._)?false:true};b.prototype.r_RV=b.prototype.S;b.prototype.Q=function(){return!(this.I_p1<=this._)?false:true};b.prototype.r_R1=b.prototype.Q;b.prototype.R=function(){return!(this.I_p2<=this._)?false:true};b.prototype.r_R2=b.prototype.R;b.prototype.Y=function(){var a;var f;var g;var h;var j;var i;var k;var l;var m;var o;var p;var n;this.C=this._;a=e(this,b.a_5,45);if(a===0){return false}this.B=this._;switch(a){case 0:return false;case 1:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}break;case 2:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'log')){return false}break;case 3:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'u')){return false}break;case 4:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'ente')){return false}break;case 5:if(!(!(this.I_p1<=this._)?false:true)){return false}if(!c(this,'')){return false}f=this.A-this._;i=true;a:while(i===true){i=false;this.C=this._;a=e(this,b.a_2,4);if(a===0){this._=this.A-f;break a}this.B=o=this._;if(!(!(this.I_p2<=o)?false:true)){this._=this.A-f;break a}if(!c(this,'')){return false}switch(a){case 0:this._=this.A-f;break a;case 1:this.C=this._;if(!d(this,2,'at')){this._=this.A-f;break a}this.B=p=this._;if(!(!(this.I_p2<=p)?false:true)){this._=this.A-f;break a}if(!c(this,'')){return false}break}}break;case 6:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}g=this.A-this._;k=true;a:while(k===true){k=false;this.C=this._;a=e(this,b.a_3,3);if(a===0){this._=this.A-g;break a}this.B=this._;switch(a){case 0:this._=this.A-g;break a;case 1:if(!(!(this.I_p2<=this._)?false:true)){this._=this.A-g;break a}if(!c(this,'')){return false}break}}break;case 7:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}h=this.A-this._;l=true;a:while(l===true){l=false;this.C=this._;a=e(this,b.a_4,3);if(a===0){this._=this.A-h;break a}this.B=this._;switch(a){case 0:this._=this.A-h;break a;case 1:if(!(!(this.I_p2<=this._)?false:true)){this._=this.A-h;break a}if(!c(this,'')){return false}break}}break;case 8:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}j=this.A-this._;m=true;a:while(m===true){m=false;this.C=this._;if(!d(this,2,'at')){this._=this.A-j;break a}this.B=n=this._;if(!(!(this.I_p2<=n)?false:true)){this._=this.A-j;break a}if(!c(this,'')){return false}}break;case 9:if(!(!(this.I_pV<=this._)?false:true)){return false}if(!d(this,1,'e')){return false}if(!c(this,'ir')){return false}break}return true};b.prototype.r_standard_suffix=b.prototype.Y;function H(a){var f;var g;var h;var i;var k;var j;var l;var m;var n;var p;var q;var o;a.C=a._;f=e(a,b.a_5,45);if(f===0){return false}a.B=a._;switch(f){case 0:return false;case 1:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}break;case 2:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'log')){return false}break;case 3:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'u')){return false}break;case 4:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'ente')){return false}break;case 5:if(!(!(a.I_p1<=a._)?false:true)){return false}if(!c(a,'')){return false}g=a.A-a._;j=true;a:while(j===true){j=false;a.C=a._;f=e(a,b.a_2,4);if(f===0){a._=a.A-g;break a}a.B=p=a._;if(!(!(a.I_p2<=p)?false:true)){a._=a.A-g;break a}if(!c(a,'')){return false}switch(f){case 0:a._=a.A-g;break a;case 1:a.C=a._;if(!d(a,2,'at')){a._=a.A-g;break a}a.B=q=a._;if(!(!(a.I_p2<=q)?false:true)){a._=a.A-g;break a}if(!c(a,'')){return false}break}}break;case 6:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}h=a.A-a._;l=true;a:while(l===true){l=false;a.C=a._;f=e(a,b.a_3,3);if(f===0){a._=a.A-h;break a}a.B=a._;switch(f){case 0:a._=a.A-h;break a;case 1:if(!(!(a.I_p2<=a._)?false:true)){a._=a.A-h;break a}if(!c(a,'')){return false}break}}break;case 7:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}i=a.A-a._;m=true;a:while(m===true){m=false;a.C=a._;f=e(a,b.a_4,3);if(f===0){a._=a.A-i;break a}a.B=a._;switch(f){case 0:a._=a.A-i;break a;case 1:if(!(!(a.I_p2<=a._)?false:true)){a._=a.A-i;break a}if(!c(a,'')){return false}break}}break;case 8:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}k=a.A-a._;n=true;a:while(n===true){n=false;a.C=a._;if(!d(a,2,'at')){a._=a.A-k;break a}a.B=o=a._;if(!(!(a.I_p2<=o)?false:true)){a._=a.A-k;break a}if(!c(a,'')){return false}}break;case 9:if(!(!(a.I_pV<=a._)?false:true)){return false}if(!d(a,1,'e')){return false}if(!c(a,'ir')){return false}break}return true};b.prototype.Z=function(){var d;var f;var a;var g;var h;var i;f=this.A-(g=this._);if(g<this.I_pV){return false}h=this._=this.I_pV;a=this.D;this.D=h;i=this._=this.A-f;this.C=i;d=e(this,b.a_6,120);if(d===0){this.D=a;return false}this.B=this._;switch(d){case 0:this.D=a;return false;case 1:if(!c(this,'')){return false}break}this.D=a;return true};b.prototype.r_verb_suffix=b.prototype.Z;function D(a){var f;var g;var d;var h;var i;var j;g=a.A-(h=a._);if(h<a.I_pV){return false}i=a._=a.I_pV;d=a.D;a.D=i;j=a._=a.A-g;a.C=j;f=e(a,b.a_6,120);if(f===0){a.D=d;return false}a.B=a._;switch(f){case 0:a.D=d;return false;case 1:if(!c(a,'')){return false}break}a.D=d;return true};b.prototype.X=function(){var a;this.C=this._;a=e(this,b.a_7,7);if(a===0){return false}this.B=this._;switch(a){case 0:return false;case 1:if(!(!(this.I_pV<=this._)?false:true)){return false}if(!c(this,'')){return false}break}return true};b.prototype.r_residual_suffix=b.prototype.X;function C(a){var d;a.C=a._;d=e(a,b.a_7,7);if(d===0){return false}a.B=a._;switch(d){case 0:return false;case 1:if(!(!(a.I_pV<=a._)?false:true)){return false}if(!c(a,'')){return false}break}return true};b.prototype.W=function(){var a;var h;var i;var j;var f;var g;var k;var l;this.C=this._;a=e(this,b.a_8,4);if(a===0){return false}this.B=this._;switch(a){case 0:return false;case 1:if(!(!(this.I_pV<=this._)?false:true)){return false}if(!c(this,'')){return false}this.C=this._;f=true;b:while(f===true){f=false;h=this.A-this._;g=true;a:while(g===true){g=false;if(!d(this,1,'u')){break a}this.B=k=this._;i=this.A-k;if(!d(this,1,'g')){break a}this._=this.A-i;break b}this._=this.A-h;if(!d(this,1,'i')){return false}this.B=l=this._;j=this.A-l;if(!d(this,1,'c')){return false}this._=this.A-j}if(!(!(this.I_pV<=this._)?false:true)){return false}if(!c(this,'')){return false}break;case 2:if(!c(this,'c')){return false}break}return true};b.prototype.r_residual_form=b.prototype.W;function y(a){var f;var i;var j;var k;var g;var h;var l;var m;a.C=a._;f=e(a,b.a_8,4);if(f===0){return false}a.B=a._;switch(f){case 0:return false;case 1:if(!(!(a.I_pV<=a._)?false:true)){return false}if(!c(a,'')){return false}a.C=a._;g=true;b:while(g===true){g=false;i=a.A-a._;h=true;a:while(h===true){h=false;if(!d(a,1,'u')){break a}a.B=l=a._;j=a.A-l;if(!d(a,1,'g')){break a}a._=a.A-j;break b}a._=a.A-i;if(!d(a,1,'i')){return false}a.B=m=a._;k=a.A-m;if(!d(a,1,'c')){return false}a._=a.A-k}if(!(!(a.I_pV<=a._)?false:true)){return false}if(!c(a,'')){return false}break;case 2:if(!c(a,'c')){return false}break}return true};b.prototype.J=function(){var q;var n;var o;var p;var r;var s;var t;var u;var v;var b;var e;var f;var g;var a;var h;var i;var j;var k;var l;var w;var x;var z;var A;var B;var I;var J;var K;var m;q=this._;b=true;a:while(b===true){b=false;if(!E(this)){break a}}w=this._=q;n=w;e=true;a:while(e===true){e=false;if(!F(this)){break a}}I=this._=n;this.D=I;K=this._=J=this.A;o=J-K;f=true;b:while(f===true){f=false;g=true;c:while(g===true){g=false;p=this.A-this._;a=true;d:while(a===true){a=false;r=this.A-this._;h=true;a:while(h===true){h=false;s=this.A-this._;i=true;e:while(i===true){i=false;if(!H(this)){break e}break a}this._=this.A-s;if(!D(this)){break d}}B=this._=(A=this.A)-r;t=A-B;j=true;a:while(j===true){j=false;this.C=this._;if(!d(this,1,'i')){break a}this.B=x=this._;u=this.A-x;if(!d(this,1,'c')){break a}z=this._=this.A-u;if(!(!(this.I_pV<=z)?false:true)){break a}if(!c(this,'')){return false}}this._=this.A-t;break c}this._=this.A-p;if(!C(this)){break b}}}this._=this.A-o;k=true;a:while(k===true){k=false;if(!y(this)){break a}}m=this._=this.D;v=m;l=true;a:while(l===true){l=false;if(!G(this)){break a}}this._=v;return true};b.prototype.stem=b.prototype.J;b.prototype.N=function(a){return a instanceof b};b.prototype.equals=b.prototype.N;b.prototype.O=function(){var c;var a;var b;var d;c='PortugueseStemmer';a=0;for(b=0;b<c.length;b++){d=c.charCodeAt(b);a=(a<<5)-a+d;a=a&a}return a|0};b.prototype.hashCode=b.prototype.O;b.serialVersionUID=1;h(b,'methodObject',function(){return new b});h(b,'a_0',function(){return[new a('',-1,3),new a('ã',0,1),new a('õ',0,2)]});h(b,'a_1',function(){return[new a('',-1,3),new a('a~',0,1),new a('o~',0,2)]});h(b,'a_2',function(){return[new a('ic',-1,-1),new a('ad',-1,-1),new a('os',-1,-1),new a('iv',-1,1)]});h(b,'a_3',function(){return[new a('ante',-1,1),new a('avel',-1,1),new a('ível',-1,1)]});h(b,'a_4',function(){return[new a('ic',-1,1),new a('abil',-1,1),new a('iv',-1,1)]});h(b,'a_5',function(){return[new a('ica',-1,1),new a('ância',-1,1),new a('ência',-1,4),new a('ira',-1,9),new a('adora',-1,1),new a('osa',-1,1),new a('ista',-1,1),new a('iva',-1,8),new a('eza',-1,1),new a('logía',-1,2),new a('idade',-1,7),new a('ante',-1,1),new a('mente',-1,6),new a('amente',12,5),new a('ável',-1,1),new a('ível',-1,1),new a('ución',-1,3),new a('ico',-1,1),new a('ismo',-1,1),new a('oso',-1,1),new a('amento',-1,1),new a('imento',-1,1),new a('ivo',-1,8),new a('aça~o',-1,1),new a('ador',-1,1),new a('icas',-1,1),new a('ências',-1,4),new a('iras',-1,9),new a('adoras',-1,1),new a('osas',-1,1),new a('istas',-1,1),new a('ivas',-1,8),new a('ezas',-1,1),new a('logías',-1,2),new a('idades',-1,7),new a('uciones',-1,3),new a('adores',-1,1),new a('antes',-1,1),new a('aço~es',-1,1),new a('icos',-1,1),new a('ismos',-1,1),new a('osos',-1,1),new a('amentos',-1,1),new a('imentos',-1,1),new a('ivos',-1,8)]});h(b,'a_6',function(){return[new a('ada',-1,1),new a('ida',-1,1),new a('ia',-1,1),new a('aria',2,1),new a('eria',2,1),new a('iria',2,1),new a('ara',-1,1),new a('era',-1,1),new a('ira',-1,1),new a('ava',-1,1),new a('asse',-1,1),new a('esse',-1,1),new a('isse',-1,1),new a('aste',-1,1),new a('este',-1,1),new a('iste',-1,1),new a('ei',-1,1),new a('arei',16,1),new a('erei',16,1),new a('irei',16,1),new a('am',-1,1),new a('iam',20,1),new a('ariam',21,1),new a('eriam',21,1),new a('iriam',21,1),new a('aram',20,1),new a('eram',20,1),new a('iram',20,1),new a('avam',20,1),new a('em',-1,1),new a('arem',29,1),new a('erem',29,1),new a('irem',29,1),new a('assem',29,1),new a('essem',29,1),new a('issem',29,1),new a('ado',-1,1),new a('ido',-1,1),new a('ando',-1,1),new a('endo',-1,1),new a('indo',-1,1),new a('ara~o',-1,1),new a('era~o',-1,1),new a('ira~o',-1,1),new a('ar',-1,1),new a('er',-1,1),new a('ir',-1,1),new a('as',-1,1),new a('adas',47,1),new a('idas',47,1),new a('ias',47,1),new a('arias',50,1),new a('erias',50,1),new a('irias',50,1),new a('aras',47,1),new a('eras',47,1),new a('iras',47,1),new a('avas',47,1),new a('es',-1,1),new a('ardes',58,1),new a('erdes',58,1),new a('irdes',58,1),new a('ares',58,1),new a('eres',58,1),new a('ires',58,1),new a('asses',58,1),new a('esses',58,1),new a('isses',58,1),new a('astes',58,1),new a('estes',58,1),new a('istes',58,1),new a('is',-1,1),new a('ais',71,1),new a('eis',71,1),new a('areis',73,1),new a('ereis',73,1),new a('ireis',73,1),new a('áreis',73,1),new a('éreis',73,1),new a('íreis',73,1),new a('ásseis',73,1),new a('ésseis',73,1),new a('ísseis',73,1),new a('áveis',73,1),new a('íeis',73,1),new a('aríeis',84,1),new a('eríeis',84,1),new a('iríeis',84,1),new a('ados',-1,1),new a('idos',-1,1),new a('amos',-1,1),new a('áramos',90,1),new a('éramos',90,1),new a('íramos',90,1),new a('ávamos',90,1),new a('íamos',90,1),new a('aríamos',95,1),new a('eríamos',95,1),new a('iríamos',95,1),new a('emos',-1,1),new a('aremos',99,1),new a('eremos',99,1),new a('iremos',99,1),new a('ássemos',99,1),new a('êssemos',99,1),new a('íssemos',99,1),new a('imos',-1,1),new a('armos',-1,1),new a('ermos',-1,1),new a('irmos',-1,1),new a('ámos',-1,1),new a('arás',-1,1),new a('erás',-1,1),new a('irás',-1,1),new a('eu',-1,1),new a('iu',-1,1),new a('ou',-1,1),new a('ará',-1,1),new a('erá',-1,1),new a('irá',-1,1)]});h(b,'a_7',function(){return[new a('a',-1,1),new a('i',-1,1),new a('o',-1,1),new a('os',-1,1),new a('á',-1,1),new a('í',-1,1),new a('ó',-1,1)]});h(b,'a_8',function(){return[new a('e',-1,1),new a('ç',-1,2),new a('é',-1,1),new a('ê',-1,1)]});h(b,'g_v',function(){return[17,65,16,0,0,0,0,0,0,0,0,0,0,0,0,0,3,19,12,2]});var o={'src/stemmer.jsx':{Stemmer:n},'src/portuguese-stemmer.jsx':{PortugueseStemmer:b}}}(JSX))
var Stemmer = JSX.require("src/portuguese-stemmer.jsx").PortugueseStemmer;
"""


class SearchPortuguese(SearchLanguage):
    lang = 'pt'
    language_name = 'Portuguese'
    js_stemmer_rawcode = 'portuguese-stemmer.js'
    js_stemmer_code = js_stemmer
    stopwords = portuguese_stopwords

    def init(self, options):
        # type: (Any) -> None
        self.stemmer = snowballstemmer.stemmer('portuguese')

    def stem(self, word):
        # type: (unicode) -> unicode
        return self.stemmer.stemWord(word.lower())
