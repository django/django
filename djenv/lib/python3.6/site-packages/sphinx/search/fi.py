# -*- coding: utf-8 -*-
"""
    sphinx.search.fi
    ~~~~~~~~~~~~~~~~

    Finnish search language: includes the JS Finnish stemmer.

    :copyright: Copyright 2007-2013 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from sphinx.search import SearchLanguage, parse_stop_word

import snowballstemmer

if False:
    # For type annotation
    from typing import Any  # NOQA


finnish_stopwords = parse_stop_word(u'''
| source: http://snowball.tartarus.org/algorithms/finnish/stop.txt
| forms of BE

olla
olen
olet
on
olemme
olette
ovat
ole        | negative form

oli
olisi
olisit
olisin
olisimme
olisitte
olisivat
olit
olin
olimme
olitte
olivat
ollut
olleet

en         | negation
et
ei
emme
ette
eivät

|Nom   Gen    Acc    Part   Iness   Elat    Illat  Adess   Ablat   Allat   Ess    Trans
minä   minun  minut  minua  minussa minusta minuun minulla minulta minulle               | I
sinä   sinun  sinut  sinua  sinussa sinusta sinuun sinulla sinulta sinulle               | you
hän    hänen  hänet  häntä  hänessä hänestä häneen hänellä häneltä hänelle               | he she
me     meidän meidät meitä  meissä  meistä  meihin meillä  meiltä  meille                | we
te     teidän teidät teitä  teissä  teistä  teihin teillä  teiltä  teille                | you
he     heidän heidät heitä  heissä  heistä  heihin heillä  heiltä  heille                | they

tämä   tämän         tätä   tässä   tästä   tähän  tällä   tältä   tälle   tänä   täksi  | this
tuo    tuon          tuota  tuossa  tuosta  tuohon tuolla  tuolta  tuolle  tuona  tuoksi | that
se     sen           sitä   siinä   siitä   siihen sillä   siltä   sille   sinä   siksi  | it
nämä   näiden        näitä  näissä  näistä  näihin näillä  näiltä  näille  näinä  näiksi | these
nuo    noiden        noita  noissa  noista  noihin noilla  noilta  noille  noina  noiksi | those
ne     niiden        niitä  niissä  niistä  niihin niillä  niiltä  niille  niinä  niiksi | they

kuka   kenen kenet   ketä   kenessä kenestä keneen kenellä keneltä kenelle kenenä keneksi| who
ketkä  keiden ketkä  keitä  keissä  keistä  keihin keillä  keiltä  keille  keinä  keiksi | (pl)
mikä   minkä minkä   mitä   missä   mistä   mihin  millä   miltä   mille   minä   miksi  | which what
mitkä                                                                                    | (pl)

joka   jonka         jota   jossa   josta   johon  jolla   jolta   jolle   jona   joksi  | who which
jotka  joiden        joita  joissa  joista  joihin joilla  joilta  joille  joina  joiksi | (pl)

| conjunctions

että   | that
ja     | and
jos    | if
koska  | because
kuin   | than
mutta  | but
niin   | so
sekä   | and
sillä  | for
tai    | or
vaan   | but
vai    | or
vaikka | although


| prepositions

kanssa  | with
mukaan  | according to
noin    | about
poikki  | across
yli     | over, across

| other

kun    | when
niin   | so
nyt    | now
itse   | self
''')

js_stemmer = u"""
var JSX={};(function(j){function l(b,e){var a=function(){};a.prototype=e.prototype;var c=new a;for(var d in b){b[d].prototype=c}}function M(c,b){for(var a in b.prototype)if(b.prototype.hasOwnProperty(a))c.prototype[a]=b.prototype[a]}function f(a,b,d){function c(a,b,c){delete a[b];a[b]=c;return c}Object.defineProperty(a,b,{get:function(){return c(a,b,d())},set:function(d){c(a,b,d)},enumerable:true,configurable:true})}function N(a,b,c){return a[b]=a[b]/c|0}var s=parseInt;var C=parseFloat;function O(a){return a!==a}var A=isFinite;var z=encodeURIComponent;var y=decodeURIComponent;var x=encodeURI;var v=decodeURI;var u=Object.prototype.toString;var E=Object.prototype.hasOwnProperty;function k(){}j.require=function(b){var a=q[b];return a!==undefined?a:null};j.profilerIsRunning=function(){return k.getResults!=null};j.getProfileResults=function(){return(k.getResults||function(){return{}})()};j.postProfileResults=function(a,b){if(k.postResults==null)throw new Error('profiler has not been turned on');return k.postResults(a,b)};j.resetProfileResults=function(){if(k.resetResults==null)throw new Error('profiler has not been turned on');return k.resetResults()};j.DEBUG=false;function t(){};l([t],Error);function b(a,b,c){this.F=a.length;this.M=a;this.N=b;this.H=c;this.G=null;this.S=null};function m(a,b,c,d,e){this.F=a.length;this.M=a;this.N=b;this.H=c;this.G=d;this.S=e};l([b,m],Object);function p(){};l([p],Object);function g(){var a;var b;var c;this.I={};a=this.E='';b=this._=0;c=this.A=a.length;this.B=0;this.C=b;this.D=c};l([g],p);function w(a,b){a.E=b.E;a._=b._;a.A=b.A;a.B=b.B;a.C=b.C;a.D=b.D};function n(b,d,c,e){var a;if(b._>=b.A){return false}a=b.E.charCodeAt(b._);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._++;return true};g.prototype.L=function(c,b,d){var a;if(this._<=this.B){return false}a=this.E.charCodeAt(this._-1);if(a>d||a<b){return false}a-=b;if((c[a>>>3]&1<<(a&7))===0){return false}this._--;return true};function h(b,d,c,e){var a;if(b._<=b.B){return false}a=b.E.charCodeAt(b._-1);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._--;return true};function o(a,d,c,e){var b;if(a._>=a.A){return false}b=a.E.charCodeAt(a._);if(b>e||b<c){a._++;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._++;return true}return false};function i(a,d,c,e){var b;if(a._<=a.B){return false}b=a.E.charCodeAt(a._-1);if(b>e||b<c){a._--;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._--;return true}return false};g.prototype.K=function(a,c){var b;if(this._-this.B<a){return false}if(this.E.slice((b=this._)-a,b)!==c){return false}this._-=a;return true};function c(a,b,d){var c;if(a._-a.B<b){return false}if(a.E.slice((c=a._)-b,c)!==d){return false}a._-=b;return true};g.prototype.Q=function(l,o){var b;var d;var e;var m;var f;var j;var k;var h;var g;var c;var a;var i;var n;b=0;d=o;e=this._;m=this.B;f=0;j=0;k=false;while(true){h=b+(d-b>>1);g=0;c=f<j?f:j;a=l[h];for(i=a.F-1-c;i>=0;i--){if(e-c===m){g=-1;break}g=this.E.charCodeAt(e-1-c)-a.M.charCodeAt(i);if(g!==0){break}c++}if(g<0){d=h;j=c}else{b=h;f=c}if(d-b<=1){if(b>0){break}if(d===b){break}if(k){break}k=true}}while(true){a=l[b];if(f>=a.F){this._=e-a.F|0;if(a.G==null){return a.H}n=a.G(this);this._=e-a.F|0;if(n){return a.H}}b=a.N;if(b<0){return 0}}return-1};function e(d,m,p){var b;var g;var e;var n;var f;var k;var l;var i;var h;var c;var a;var j;var o;b=0;g=p;e=d._;n=d.B;f=0;k=0;l=false;while(true){i=b+(g-b>>1);h=0;c=f<k?f:k;a=m[i];for(j=a.F-1-c;j>=0;j--){if(e-c===n){h=-1;break}h=d.E.charCodeAt(e-1-c)-a.M.charCodeAt(j);if(h!==0){break}c++}if(h<0){g=i;k=c}else{b=i;f=c}if(g-b<=1){if(b>0){break}if(g===b){break}if(l){break}l=true}}while(true){a=m[b];if(f>=a.F){d._=e-a.F|0;if(a.G==null){return a.H}o=a.G(d);d._=e-a.F|0;if(o){return a.H}}b=a.N;if(b<0){return 0}}return-1};function D(a,b,d,e){var c;c=e.length-(d-b);a.E=a.E.slice(0,b)+e+a.E.slice(d);a.A+=c|0;if(a._>=d){a._+=c|0}else if(a._>b){a._=b}return c|0};function d(a,f){var b;var c;var d;var e;b=false;if((c=a.C)<0||c>(d=a.D)||d>(e=a.A)||e>a.E.length?false:true){D(a,a.C,a.D,f);b=true}return b};function r(a,f){var b;var c;var d;var e;b='';if((c=a.C)<0||c>(d=a.D)||d>(e=a.A)||e>a.E.length?false:true){b=a.E.slice(a.C,a.D)}return b};g.prototype.J=function(){return false};g.prototype.e=function(b){var a;var c;var d;var e;a=this.I['.'+b];if(a==null){c=this.E=b;d=this._=0;e=this.A=c.length;this.B=0;this.C=d;this.D=e;this.J();a=this.E;this.I['.'+b]=a}return a};g.prototype.stemWord=g.prototype.e;g.prototype.f=function(e){var d;var b;var c;var a;var f;var g;var h;d=[];for(b=0;b<e.length;b++){c=e[b];a=this.I['.'+c];if(a==null){f=this.E=c;g=this._=0;h=this.A=f.length;this.B=0;this.C=g;this.D=h;this.J();a=this.E;this.I['.'+c]=a}d.push(a)}return d};g.prototype.stemWords=g.prototype.f;function a(){g.call(this);this.B_ending_removed=false;this.S_x='';this.I_p2=0;this.I_p1=0};l([a],g);a.prototype.O=function(a){this.B_ending_removed=a.B_ending_removed;this.S_x=a.S_x;this.I_p2=a.I_p2;this.I_p1=a.I_p1;w(this,a)};a.prototype.copy_from=a.prototype.O;a.prototype.Y=function(){var b;var c;var d;var e;var f;var g;var h;var i;var j;this.I_p1=i=this.A;this.I_p2=i;a:while(true){b=this._;d=true;b:while(d===true){d=false;if(!n(this,a.g_V1,97,246)){break b}this._=b;break a}h=this._=b;if(h>=this.A){return false}this._++}a:while(true){e=true;b:while(e===true){e=false;if(!o(this,a.g_V1,97,246)){break b}break a}if(this._>=this.A){return false}this._++}this.I_p1=this._;a:while(true){c=this._;f=true;b:while(f===true){f=false;if(!n(this,a.g_V1,97,246)){break b}this._=c;break a}j=this._=c;if(j>=this.A){return false}this._++}a:while(true){g=true;b:while(g===true){g=false;if(!o(this,a.g_V1,97,246)){break b}break a}if(this._>=this.A){return false}this._++}this.I_p2=this._;return true};a.prototype.r_mark_regions=a.prototype.Y;function H(b){var d;var e;var f;var c;var g;var h;var j;var k;var i;b.I_p1=k=b.A;b.I_p2=k;a:while(true){d=b._;f=true;b:while(f===true){f=false;if(!n(b,a.g_V1,97,246)){break b}b._=d;break a}j=b._=d;if(j>=b.A){return false}b._++}a:while(true){c=true;b:while(c===true){c=false;if(!o(b,a.g_V1,97,246)){break b}break a}if(b._>=b.A){return false}b._++}b.I_p1=b._;a:while(true){e=b._;g=true;b:while(g===true){g=false;if(!n(b,a.g_V1,97,246)){break b}b._=e;break a}i=b._=e;if(i>=b.A){return false}b._++}a:while(true){h=true;b:while(h===true){h=false;if(!o(b,a.g_V1,97,246)){break b}break a}if(b._>=b.A){return false}b._++}b.I_p2=b._;return true};a.prototype.U=function(){return!(this.I_p2<=this._)?false:true};a.prototype.r_R2=a.prototype.U;a.prototype.a=function(){var b;var f;var c;var g;var i;var j;f=this.A-(g=this._);if(g<this.I_p1){return false}i=this._=this.I_p1;c=this.B;this.B=i;j=this._=this.A-f;this.D=j;b=e(this,a.a_0,10);if(b===0){this.B=c;return false}this.C=this._;this.B=c;switch(b){case 0:return false;case 1:if(!h(this,a.g_particle_end,97,246)){return false}break;case 2:if(!(!(this.I_p2<=this._)?false:true)){return false}break}return!d(this,'')?false:true};a.prototype.r_particle_etc=a.prototype.a;function I(b){var c;var g;var f;var i;var j;var k;g=b.A-(i=b._);if(i<b.I_p1){return false}j=b._=b.I_p1;f=b.B;b.B=j;k=b._=b.A-g;b.D=k;c=e(b,a.a_0,10);if(c===0){b.B=f;return false}b.C=b._;b.B=f;switch(c){case 0:return false;case 1:if(!h(b,a.g_particle_end,97,246)){return false}break;case 2:if(!(!(b.I_p2<=b._)?false:true)){return false}break}return!d(b,'')?false:true};a.prototype.b=function(){var b;var h;var f;var i;var g;var j;var k;var l;h=this.A-(j=this._);if(j<this.I_p1){return false}k=this._=this.I_p1;f=this.B;this.B=k;l=this._=this.A-h;this.D=l;b=e(this,a.a_4,9);if(b===0){this.B=f;return false}this.C=this._;this.B=f;switch(b){case 0:return false;case 1:i=this.A-this._;g=true;a:while(g===true){g=false;if(!c(this,1,'k')){break a}return false}this._=this.A-i;if(!d(this,'')){return false}break;case 2:if(!d(this,'')){return false}this.D=this._;if(!c(this,3,'kse')){return false}this.C=this._;if(!d(this,'ksi')){return false}break;case 3:if(!d(this,'')){return false}break;case 4:if(e(this,a.a_1,6)===0){return false}if(!d(this,'')){return false}break;case 5:if(e(this,a.a_2,6)===0){return false}if(!d(this,'')){return false}break;case 6:if(e(this,a.a_3,2)===0){return false}if(!d(this,'')){return false}break}return true};a.prototype.r_possessive=a.prototype.b;function J(b){var f;var i;var g;var j;var h;var k;var l;var m;i=b.A-(k=b._);if(k<b.I_p1){return false}l=b._=b.I_p1;g=b.B;b.B=l;m=b._=b.A-i;b.D=m;f=e(b,a.a_4,9);if(f===0){b.B=g;return false}b.C=b._;b.B=g;switch(f){case 0:return false;case 1:j=b.A-b._;h=true;a:while(h===true){h=false;if(!c(b,1,'k')){break a}return false}b._=b.A-j;if(!d(b,'')){return false}break;case 2:if(!d(b,'')){return false}b.D=b._;if(!c(b,3,'kse')){return false}b.C=b._;if(!d(b,'ksi')){return false}break;case 3:if(!d(b,'')){return false}break;case 4:if(e(b,a.a_1,6)===0){return false}if(!d(b,'')){return false}break;case 5:if(e(b,a.a_2,6)===0){return false}if(!d(b,'')){return false}break;case 6:if(e(b,a.a_3,2)===0){return false}if(!d(b,'')){return false}break}return true};a.prototype.T=function(){return e(this,a.a_5,7)===0?false:true};a.prototype.r_LONG=a.prototype.T;a.prototype.V=function(){return!c(this,1,'i')?false:!h(this,a.g_V2,97,246)?false:true};a.prototype.r_VI=a.prototype.V;a.prototype.W=function(){var j;var o;var f;var g;var p;var m;var b;var k;var l;var q;var r;var s;var n;o=this.A-(q=this._);if(q<this.I_p1){return false}r=this._=this.I_p1;f=this.B;this.B=r;s=this._=this.A-o;this.D=s;j=e(this,a.a_6,30);if(j===0){this.B=f;return false}this.C=this._;this.B=f;switch(j){case 0:return false;case 1:if(!c(this,1,'a')){return false}break;case 2:if(!c(this,1,'e')){return false}break;case 3:if(!c(this,1,'i')){return false}break;case 4:if(!c(this,1,'o')){return false}break;case 5:if(!c(this,1,'ä')){return false}break;case 6:if(!c(this,1,'ö')){return false}break;case 7:g=this.A-this._;b=true;a:while(b===true){b=false;p=this.A-this._;k=true;b:while(k===true){k=false;m=this.A-this._;l=true;c:while(l===true){l=false;if(!(e(this,a.a_5,7)===0?false:true)){break c}break b}this._=this.A-m;if(!c(this,2,'ie')){this._=this.A-g;break a}}n=this._=this.A-p;if(n<=this.B){this._=this.A-g;break a}this._--;this.C=this._}break;case 8:if(!h(this,a.g_V1,97,246)){return false}if(!i(this,a.g_V1,97,246)){return false}break;case 9:if(!c(this,1,'e')){return false}break}if(!d(this,'')){return false}this.B_ending_removed=true;return true};a.prototype.r_case_ending=a.prototype.W;function K(b){var f;var o;var g;var j;var p;var n;var k;var l;var m;var r;var s;var t;var q;o=b.A-(r=b._);if(r<b.I_p1){return false}s=b._=b.I_p1;g=b.B;b.B=s;t=b._=b.A-o;b.D=t;f=e(b,a.a_6,30);if(f===0){b.B=g;return false}b.C=b._;b.B=g;switch(f){case 0:return false;case 1:if(!c(b,1,'a')){return false}break;case 2:if(!c(b,1,'e')){return false}break;case 3:if(!c(b,1,'i')){return false}break;case 4:if(!c(b,1,'o')){return false}break;case 5:if(!c(b,1,'ä')){return false}break;case 6:if(!c(b,1,'ö')){return false}break;case 7:j=b.A-b._;k=true;a:while(k===true){k=false;p=b.A-b._;l=true;b:while(l===true){l=false;n=b.A-b._;m=true;c:while(m===true){m=false;if(!(e(b,a.a_5,7)===0?false:true)){break c}break b}b._=b.A-n;if(!c(b,2,'ie')){b._=b.A-j;break a}}q=b._=b.A-p;if(q<=b.B){b._=b.A-j;break a}b._--;b.C=b._}break;case 8:if(!h(b,a.g_V1,97,246)){return false}if(!i(b,a.g_V1,97,246)){return false}break;case 9:if(!c(b,1,'e')){return false}break}if(!d(b,'')){return false}b.B_ending_removed=true;return true};a.prototype.Z=function(){var b;var h;var f;var i;var g;var j;var k;var l;h=this.A-(j=this._);if(j<this.I_p2){return false}k=this._=this.I_p2;f=this.B;this.B=k;l=this._=this.A-h;this.D=l;b=e(this,a.a_7,14);if(b===0){this.B=f;return false}this.C=this._;this.B=f;switch(b){case 0:return false;case 1:i=this.A-this._;g=true;a:while(g===true){g=false;if(!c(this,2,'po')){break a}return false}this._=this.A-i;break}return!d(this,'')?false:true};a.prototype.r_other_endings=a.prototype.Z;function L(b){var f;var i;var g;var j;var h;var k;var l;var m;i=b.A-(k=b._);if(k<b.I_p2){return false}l=b._=b.I_p2;g=b.B;b.B=l;m=b._=b.A-i;b.D=m;f=e(b,a.a_7,14);if(f===0){b.B=g;return false}b.C=b._;b.B=g;switch(f){case 0:return false;case 1:j=b.A-b._;h=true;a:while(h===true){h=false;if(!c(b,2,'po')){break a}return false}b._=b.A-j;break}return!d(b,'')?false:true};a.prototype.X=function(){var c;var b;var f;var g;var h;c=this.A-(f=this._);if(f<this.I_p1){return false}g=this._=this.I_p1;b=this.B;this.B=g;h=this._=this.A-c;this.D=h;if(e(this,a.a_8,2)===0){this.B=b;return false}this.C=this._;this.B=b;return!d(this,'')?false:true};a.prototype.r_i_plural=a.prototype.X;function G(b){var f;var c;var g;var h;var i;f=b.A-(g=b._);if(g<b.I_p1){return false}h=b._=b.I_p1;c=b.B;b.B=h;i=b._=b.A-f;b.D=i;if(e(b,a.a_8,2)===0){b.B=c;return false}b.C=b._;b.B=c;return!d(b,'')?false:true};a.prototype.c=function(){var i;var l;var b;var j;var k;var g;var m;var f;var o;var p;var q;var r;var s;var t;var n;l=this.A-(o=this._);if(o<this.I_p1){return false}p=this._=this.I_p1;b=this.B;this.B=p;q=this._=this.A-l;this.D=q;if(!c(this,1,'t')){this.B=b;return false}this.C=r=this._;j=this.A-r;if(!h(this,a.g_V1,97,246)){this.B=b;return false}this._=this.A-j;if(!d(this,'')){return false}this.B=b;k=this.A-(s=this._);if(s<this.I_p2){return false}t=this._=this.I_p2;g=this.B;this.B=t;n=this._=this.A-k;this.D=n;i=e(this,a.a_9,2);if(i===0){this.B=g;return false}this.C=this._;this.B=g;switch(i){case 0:return false;case 1:m=this.A-this._;f=true;a:while(f===true){f=false;if(!c(this,2,'po')){break a}return false}this._=this.A-m;break}return!d(this,'')?false:true};a.prototype.r_t_plural=a.prototype.c;function F(b){var g;var m;var f;var o;var l;var i;var k;var j;var p;var q;var r;var s;var t;var u;var n;m=b.A-(p=b._);if(p<b.I_p1){return false}q=b._=b.I_p1;f=b.B;b.B=q;r=b._=b.A-m;b.D=r;if(!c(b,1,'t')){b.B=f;return false}b.C=s=b._;o=b.A-s;if(!h(b,a.g_V1,97,246)){b.B=f;return false}b._=b.A-o;if(!d(b,'')){return false}b.B=f;l=b.A-(t=b._);if(t<b.I_p2){return false}u=b._=b.I_p2;i=b.B;b.B=u;n=b._=b.A-l;b.D=n;g=e(b,a.a_9,2);if(g===0){b.B=i;return false}b.C=b._;b.B=i;switch(g){case 0:return false;case 1:k=b.A-b._;j=true;a:while(j===true){j=false;if(!c(b,2,'po')){break a}return false}b._=b.A-k;break}return!d(b,'')?false:true};a.prototype.d=function(){var x;var q;var s;var t;var u;var v;var w;var y;var f;var g;var j;var k;var l;var m;var n;var b;var o;var z;var p;var B;var C;var D;var E;var F;var G;var H;var I;var J;var K;var L;var A;x=this.A-(z=this._);if(z<this.I_p1){return false}B=this._=this.I_p1;q=this.B;this.B=B;D=this._=(C=this.A)-x;s=C-D;g=true;a:while(g===true){g=false;t=this.A-this._;if(!(e(this,a.a_5,7)===0?false:true)){break a}p=this._=this.A-t;this.D=p;if(p<=this.B){break a}this._--;this.C=this._;if(!d(this,'')){return false}}F=this._=(E=this.A)-s;u=E-F;j=true;a:while(j===true){j=false;this.D=this._;if(!h(this,a.g_AEI,97,228)){break a}this.C=this._;if(!i(this,a.g_V1,97,246)){break a}if(!d(this,'')){return false}}H=this._=(G=this.A)-u;v=G-H;k=true;a:while(k===true){k=false;this.D=this._;if(!c(this,1,'j')){break a}this.C=this._;l=true;b:while(l===true){l=false;w=this.A-this._;m=true;c:while(m===true){m=false;if(!c(this,1,'o')){break c}break b}this._=this.A-w;if(!c(this,1,'u')){break a}}if(!d(this,'')){return false}}J=this._=(I=this.A)-v;y=I-J;n=true;a:while(n===true){n=false;this.D=this._;if(!c(this,1,'o')){break a}this.C=this._;if(!c(this,1,'j')){break a}if(!d(this,'')){return false}}this._=this.A-y;this.B=q;a:while(true){f=this.A-this._;b=true;b:while(b===true){b=false;if(!i(this,a.g_V1,97,246)){break b}this._=this.A-f;break a}K=this._=this.A-f;if(K<=this.B){return false}this._--}this.D=L=this._;if(L<=this.B){return false}this._--;this.C=this._;A=this.S_x=r(this,this.S_x);return A===''?false:!(o=this.S_x,c(this,o.length,o))?false:!d(this,'')?false:true};a.prototype.r_tidy=a.prototype.d;function B(b){var s;var t;var u;var v;var w;var x;var y;var z;var l;var g;var j;var k;var f;var m;var n;var o;var p;var A;var q;var C;var D;var E;var F;var G;var H;var I;var J;var K;var L;var M;var B;s=b.A-(A=b._);if(A<b.I_p1){return false}C=b._=b.I_p1;t=b.B;b.B=C;E=b._=(D=b.A)-s;u=D-E;g=true;a:while(g===true){g=false;v=b.A-b._;if(!(e(b,a.a_5,7)===0?false:true)){break a}q=b._=b.A-v;b.D=q;if(q<=b.B){break a}b._--;b.C=b._;if(!d(b,'')){return false}}G=b._=(F=b.A)-u;w=F-G;j=true;a:while(j===true){j=false;b.D=b._;if(!h(b,a.g_AEI,97,228)){break a}b.C=b._;if(!i(b,a.g_V1,97,246)){break a}if(!d(b,'')){return false}}I=b._=(H=b.A)-w;x=H-I;k=true;a:while(k===true){k=false;b.D=b._;if(!c(b,1,'j')){break a}b.C=b._;f=true;b:while(f===true){f=false;y=b.A-b._;m=true;c:while(m===true){m=false;if(!c(b,1,'o')){break c}break b}b._=b.A-y;if(!c(b,1,'u')){break a}}if(!d(b,'')){return false}}K=b._=(J=b.A)-x;z=J-K;n=true;a:while(n===true){n=false;b.D=b._;if(!c(b,1,'o')){break a}b.C=b._;if(!c(b,1,'j')){break a}if(!d(b,'')){return false}}b._=b.A-z;b.B=t;a:while(true){l=b.A-b._;o=true;b:while(o===true){o=false;if(!i(b,a.g_V1,97,246)){break b}b._=b.A-l;break a}L=b._=b.A-l;if(L<=b.B){return false}b._--}b.D=M=b._;if(M<=b.B){return false}b._--;b.C=b._;B=b.S_x=r(b,b.S_x);return B===''?false:!(p=b.S_x,c(b,p.length,p))?false:!d(b,'')?false:true};a.prototype.J=function(){var p;var k;var l;var m;var n;var o;var q;var r;var b;var c;var d;var e;var f;var g;var a;var h;var i;var j;var t;var u;var v;var w;var x;var y;var z;var A;var C;var D;var s;p=this._;b=true;a:while(b===true){b=false;if(!H(this)){break a}}t=this._=p;this.B_ending_removed=false;this.B=t;v=this._=u=this.A;k=u-v;c=true;a:while(c===true){c=false;if(!I(this)){break a}}x=this._=(w=this.A)-k;l=w-x;d=true;a:while(d===true){d=false;if(!J(this)){break a}}z=this._=(y=this.A)-l;m=y-z;e=true;a:while(e===true){e=false;if(!K(this)){break a}}C=this._=(A=this.A)-m;n=A-C;f=true;a:while(f===true){f=false;if(!L(this)){break a}}this._=this.A-n;g=true;a:while(g===true){g=false;o=this.A-this._;a=true;b:while(a===true){a=false;if(!this.B_ending_removed){break b}q=this.A-this._;h=true;c:while(h===true){h=false;if(!G(this)){break c}}this._=this.A-q;break a}s=this._=(D=this.A)-o;r=D-s;i=true;b:while(i===true){i=false;if(!F(this)){break b}}this._=this.A-r}j=true;a:while(j===true){j=false;if(!B(this)){break a}}this._=this.B;return true};a.prototype.stem=a.prototype.J;a.prototype.P=function(b){return b instanceof a};a.prototype.equals=a.prototype.P;a.prototype.R=function(){var c;var a;var b;var d;c='FinnishStemmer';a=0;for(b=0;b<c.length;b++){d=c.charCodeAt(b);a=(a<<5)-a+d;a=a&a}return a|0};a.prototype.hashCode=a.prototype.R;a.serialVersionUID=1;f(a,'methodObject',function(){return new a});f(a,'a_0',function(){return[new b('pa',-1,1),new b('sti',-1,2),new b('kaan',-1,1),new b('han',-1,1),new b('kin',-1,1),new b('hän',-1,1),new b('kään',-1,1),new b('ko',-1,1),new b('pä',-1,1),new b('kö',-1,1)]});f(a,'a_1',function(){return[new b('lla',-1,-1),new b('na',-1,-1),new b('ssa',-1,-1),new b('ta',-1,-1),new b('lta',3,-1),new b('sta',3,-1)]});f(a,'a_2',function(){return[new b('llä',-1,-1),new b('nä',-1,-1),new b('ssä',-1,-1),new b('tä',-1,-1),new b('ltä',3,-1),new b('stä',3,-1)]});f(a,'a_3',function(){return[new b('lle',-1,-1),new b('ine',-1,-1)]});f(a,'a_4',function(){return[new b('nsa',-1,3),new b('mme',-1,3),new b('nne',-1,3),new b('ni',-1,2),new b('si',-1,1),new b('an',-1,4),new b('en',-1,6),new b('än',-1,5),new b('nsä',-1,3)]});f(a,'a_5',function(){return[new b('aa',-1,-1),new b('ee',-1,-1),new b('ii',-1,-1),new b('oo',-1,-1),new b('uu',-1,-1),new b('ää',-1,-1),new b('öö',-1,-1)]});f(a,'a_6',function(){return[new b('a',-1,8),new b('lla',0,-1),new b('na',0,-1),new b('ssa',0,-1),new b('ta',0,-1),new b('lta',4,-1),new b('sta',4,-1),new b('tta',4,9),new b('lle',-1,-1),new b('ine',-1,-1),new b('ksi',-1,-1),new b('n',-1,7),new b('han',11,1),new m('den',11,-1,function(c){var b;b=c;return!b.K(1,'i')?false:!b.L(a.g_V2,97,246)?false:true},a.methodObject),new m('seen',11,-1,function(c){var b;b=c;return b.Q(a.a_5,7)===0?false:true},a.methodObject),new b('hen',11,2),new m('tten',11,-1,function(c){var b;b=c;return!b.K(1,'i')?false:!b.L(a.g_V2,97,246)?false:true},a.methodObject),new b('hin',11,3),new m('siin',11,-1,function(c){var b;b=c;return!b.K(1,'i')?false:!b.L(a.g_V2,97,246)?false:true},a.methodObject),new b('hon',11,4),new b('hän',11,5),new b('hön',11,6),new b('ä',-1,8),new b('llä',22,-1),new b('nä',22,-1),new b('ssä',22,-1),new b('tä',22,-1),new b('ltä',26,-1),new b('stä',26,-1),new b('ttä',26,9)]});f(a,'a_7',function(){return[new b('eja',-1,-1),new b('mma',-1,1),new b('imma',1,-1),new b('mpa',-1,1),new b('impa',3,-1),new b('mmi',-1,1),new b('immi',5,-1),new b('mpi',-1,1),new b('impi',7,-1),new b('ejä',-1,-1),new b('mmä',-1,1),new b('immä',10,-1),new b('mpä',-1,1),new b('impä',12,-1)]});f(a,'a_8',function(){return[new b('i',-1,-1),new b('j',-1,-1)]});f(a,'a_9',function(){return[new b('mma',-1,1),new b('imma',0,-1)]});f(a,'g_AEI',function(){return[17,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,8]});f(a,'g_V1',function(){return[17,65,16,1,0,0,0,0,0,0,0,0,0,0,0,0,8,0,32]});f(a,'g_V2',function(){return[17,65,16,0,0,0,0,0,0,0,0,0,0,0,0,0,8,0,32]});f(a,'g_particle_end',function(){return[17,97,24,1,0,0,0,0,0,0,0,0,0,0,0,0,8,0,32]});var q={'src/stemmer.jsx':{Stemmer:p},'src/finnish-stemmer.jsx':{FinnishStemmer:a}}}(JSX))
var Stemmer = JSX.require("src/finnish-stemmer.jsx").FinnishStemmer;
"""


class SearchFinnish(SearchLanguage):
    lang = 'fi'
    language_name = 'Finnish'
    js_stemmer_rawcode = 'finnish-stemmer.js'
    js_stemmer_code = js_stemmer
    stopwords = finnish_stopwords

    def init(self, options):
        # type: (Any) -> None
        self.stemmer = snowballstemmer.stemmer('finnish')

    def stem(self, word):
        # type: (unicode) -> unicode
        return self.stemmer.stemWord(word.lower())
