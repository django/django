# -*- coding: utf-8 -*-
"""
    sphinx.search.sv
    ~~~~~~~~~~~~~~~~

    Swedish search language: includes the JS Swedish stemmer.

    :copyright: Copyright 2007-2013 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from sphinx.search import SearchLanguage, parse_stop_word

import snowballstemmer

if False:
    # For type annotation
    from typing import Any

swedish_stopwords = parse_stop_word(u'''
| source: http://snowball.tartarus.org/algorithms/swedish/stop.txt
och            | and
det            | it, this/that
att            | to (with infinitive)
i              | in, at
en             | a
jag            | I
hon            | she
som            | who, that
han            | he
på             | on
den            | it, this/that
med            | with
var            | where, each
sig            | him(self) etc
för            | for
så             | so (also: seed)
till           | to
är             | is
men            | but
ett            | a
om             | if; around, about
hade           | had
de             | they, these/those
av             | of
icke           | not, no
mig            | me
du             | you
henne          | her
då             | then, when
sin            | his
nu             | now
har            | have
inte           | inte någon = no one
hans           | his
honom          | him
skulle         | 'sake'
hennes         | her
där            | there
min            | my
man            | one (pronoun)
ej             | nor
vid            | at, by, on (also: vast)
kunde          | could
något          | some etc
från           | from, off
ut             | out
när            | when
efter          | after, behind
upp            | up
vi             | we
dem            | them
vara           | be
vad            | what
över           | over
än             | than
dig            | you
kan            | can
sina           | his
här            | here
ha             | have
mot            | towards
alla           | all
under          | under (also: wonder)
någon          | some etc
eller          | or (else)
allt           | all
mycket         | much
sedan          | since
ju             | why
denna          | this/that
själv          | myself, yourself etc
detta          | this/that
åt             | to
utan           | without
varit          | was
hur            | how
ingen          | no
mitt           | my
ni             | you
bli            | to be, become
blev           | from bli
oss            | us
din            | thy
dessa          | these/those
några          | some etc
deras          | their
blir           | from bli
mina           | my
samma          | (the) same
vilken         | who, that
er             | you, your
sådan          | such a
vår            | our
blivit         | from bli
dess           | its
inom           | within
mellan         | between
sådant         | such a
varför         | why
varje          | each
vilka          | who, that
ditt           | thy
vem            | who
vilket         | who, that
sitta          | his
sådana         | such a
vart           | each
dina           | thy
vars           | whose
vårt           | our
våra           | our
ert            | your
era            | your
vilkas         | whose
''')

js_stemmer = u"""
var JSX={};(function(e){function i(b,e){var a=function(){};a.prototype=e.prototype;var c=new a;for(var d in b){b[d].prototype=c}}function G(c,b){for(var a in b.prototype)if(b.prototype.hasOwnProperty(a))c.prototype[a]=b.prototype[a]}function h(a,b,d){function c(a,b,c){delete a[b];a[b]=c;return c}Object.defineProperty(a,b,{get:function(){return c(a,b,d())},set:function(d){c(a,b,d)},enumerable:true,configurable:true})}function F(a,b,c){return a[b]=a[b]/c|0}var t=parseInt;var u=parseFloat;function E(a){return a!==a}var x=isFinite;var y=encodeURIComponent;var z=decodeURIComponent;var B=encodeURI;var C=decodeURI;var o=Object.prototype.toString;var p=Object.prototype.hasOwnProperty;function f(){}e.require=function(b){var a=n[b];return a!==undefined?a:null};e.profilerIsRunning=function(){return f.getResults!=null};e.getProfileResults=function(){return(f.getResults||function(){return{}})()};e.postProfileResults=function(a,b){if(f.postResults==null)throw new Error('profiler has not been turned on');return f.postResults(a,b)};e.resetProfileResults=function(){if(f.resetResults==null)throw new Error('profiler has not been turned on');return f.resetResults()};e.DEBUG=false;function r(){};i([r],Error);function a(a,b,c){this.G=a.length;this.R=a;this.U=b;this.J=c;this.I=null;this.V=null};i([a],Object);function j(){};i([j],Object);function d(){var a;var b;var c;this.F={};a=this.C='';b=this._=0;c=this.B=a.length;this.A=0;this.D=b;this.E=c};i([d],j);function v(a,b){a.C=b.C;a._=b._;a.B=b.B;a.A=b.A;a.D=b.D;a.E=b.E};function k(b,d,c,e){var a;if(b._>=b.B){return false}a=b.C.charCodeAt(b._);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._++;return true};function l(b,d,c,e){var a;if(b._<=b.A){return false}a=b.C.charCodeAt(b._-1);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._--;return true};function m(a,d,c,e){var b;if(a._>=a.B){return false}b=a.C.charCodeAt(a._);if(b>e||b<c){a._++;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._++;return true}return false};function g(d,m,p){var b;var g;var e;var n;var f;var k;var l;var i;var h;var c;var a;var j;var o;b=0;g=p;e=d._;n=d.A;f=0;k=0;l=false;while(true){i=b+(g-b>>1);h=0;c=f<k?f:k;a=m[i];for(j=a.G-1-c;j>=0;j--){if(e-c===n){h=-1;break}h=d.C.charCodeAt(e-1-c)-a.R.charCodeAt(j);if(h!==0){break}c++}if(h<0){g=i;k=c}else{b=i;f=c}if(g-b<=1){if(b>0){break}if(g===b){break}if(l){break}l=true}}while(true){a=m[b];if(f>=a.G){d._=e-a.G|0;if(a.I==null){return a.J}o=a.I(d);d._=e-a.G|0;if(o){return a.J}}b=a.U;if(b<0){return 0}}return-1};function A(a,b,d,e){var c;c=e.length-(d-b);a.C=a.C.slice(0,b)+e+a.C.slice(d);a.B+=c|0;if(a._>=d){a._+=c|0}else if(a._>b){a._=b}return c|0};function c(a,f){var b;var c;var d;var e;b=false;if((c=a.D)<0||c>(d=a.E)||d>(e=a.B)||e>a.C.length?false:true){A(a,a.D,a.E,f);b=true}return b};d.prototype.H=function(){return false};d.prototype.S=function(b){var a;var c;var d;var e;a=this.F['.'+b];if(a==null){c=this.C=b;d=this._=0;e=this.B=c.length;this.A=0;this.D=d;this.E=e;this.H();a=this.C;this.F['.'+b]=a}return a};d.prototype.stemWord=d.prototype.S;d.prototype.T=function(e){var d;var b;var c;var a;var f;var g;var h;d=[];for(b=0;b<e.length;b++){c=e[b];a=this.F['.'+c];if(a==null){f=this.C=c;g=this._=0;h=this.B=f.length;this.A=0;this.D=g;this.E=h;this.H();a=this.C;this.F['.'+c]=a}d.push(a)}return d};d.prototype.stemWords=d.prototype.T;function b(){d.call(this);this.I_x=0;this.I_p1=0};i([b],d);b.prototype.K=function(a){this.I_x=a.I_x;this.I_p1=a.I_p1;v(this,a)};b.prototype.copy_from=b.prototype.K;b.prototype.P=function(){var g;var d;var a;var e;var c;var f;var i;var j;var l;var h;this.I_p1=j=this.B;g=i=this._;a=i+3|0;if(0>a||a>j){return false}h=this._=a;this.I_x=h;this._=g;a:while(true){d=this._;e=true;b:while(e===true){e=false;if(!k(this,b.g_v,97,246)){break b}this._=d;break a}l=this._=d;if(l>=this.B){return false}this._++}a:while(true){c=true;b:while(c===true){c=false;if(!m(this,b.g_v,97,246)){break b}break a}if(this._>=this.B){return false}this._++}this.I_p1=this._;f=true;a:while(f===true){f=false;if(!(this.I_p1<this.I_x)){break a}this.I_p1=this.I_x}return true};b.prototype.r_mark_regions=b.prototype.P;function D(a){var h;var e;var c;var f;var d;var g;var j;var l;var n;var i;a.I_p1=l=a.B;h=j=a._;c=j+3|0;if(0>c||c>l){return false}i=a._=c;a.I_x=i;a._=h;a:while(true){e=a._;f=true;b:while(f===true){f=false;if(!k(a,b.g_v,97,246)){break b}a._=e;break a}n=a._=e;if(n>=a.B){return false}a._++}a:while(true){d=true;b:while(d===true){d=false;if(!m(a,b.g_v,97,246)){break b}break a}if(a._>=a.B){return false}a._++}a.I_p1=a._;g=true;a:while(g===true){g=false;if(!(a.I_p1<a.I_x)){break a}a.I_p1=a.I_x}return true};b.prototype.O=function(){var a;var e;var d;var f;var h;var i;e=this.B-(f=this._);if(f<this.I_p1){return false}h=this._=this.I_p1;d=this.A;this.A=h;i=this._=this.B-e;this.E=i;a=g(this,b.a_0,37);if(a===0){this.A=d;return false}this.D=this._;this.A=d;switch(a){case 0:return false;case 1:if(!c(this,'')){return false}break;case 2:if(!l(this,b.g_s_ending,98,121)){return false}if(!c(this,'')){return false}break}return true};b.prototype.r_main_suffix=b.prototype.O;function w(a){var d;var f;var e;var h;var i;var j;f=a.B-(h=a._);if(h<a.I_p1){return false}i=a._=a.I_p1;e=a.A;a.A=i;j=a._=a.B-f;a.E=j;d=g(a,b.a_0,37);if(d===0){a.A=e;return false}a.D=a._;a.A=e;switch(d){case 0:return false;case 1:if(!c(a,'')){return false}break;case 2:if(!l(a,b.g_s_ending,98,121)){return false}if(!c(a,'')){return false}break}return true};b.prototype.N=function(){var e;var a;var f;var h;var i;var j;var k;var d;e=this.B-(h=this._);if(h<this.I_p1){return false}i=this._=this.I_p1;a=this.A;this.A=i;k=this._=(j=this.B)-e;f=j-k;if(g(this,b.a_1,7)===0){this.A=a;return false}d=this._=this.B-f;this.E=d;if(d<=this.A){this.A=a;return false}this._--;this.D=this._;if(!c(this,'')){return false}this.A=a;return true};b.prototype.r_consonant_pair=b.prototype.N;function s(a){var f;var d;var h;var i;var j;var k;var l;var e;f=a.B-(i=a._);if(i<a.I_p1){return false}j=a._=a.I_p1;d=a.A;a.A=j;l=a._=(k=a.B)-f;h=k-l;if(g(a,b.a_1,7)===0){a.A=d;return false}e=a._=a.B-h;a.E=e;if(e<=a.A){a.A=d;return false}a._--;a.D=a._;if(!c(a,'')){return false}a.A=d;return true};b.prototype.Q=function(){var d;var e;var a;var f;var h;var i;e=this.B-(f=this._);if(f<this.I_p1){return false}h=this._=this.I_p1;a=this.A;this.A=h;i=this._=this.B-e;this.E=i;d=g(this,b.a_2,5);if(d===0){this.A=a;return false}this.D=this._;switch(d){case 0:this.A=a;return false;case 1:if(!c(this,'')){return false}break;case 2:if(!c(this,'lös')){return false}break;case 3:if(!c(this,'full')){return false}break}this.A=a;return true};b.prototype.r_other_suffix=b.prototype.Q;function q(a){var e;var f;var d;var h;var i;var j;f=a.B-(h=a._);if(h<a.I_p1){return false}i=a._=a.I_p1;d=a.A;a.A=i;j=a._=a.B-f;a.E=j;e=g(a,b.a_2,5);if(e===0){a.A=d;return false}a.D=a._;switch(e){case 0:a.A=d;return false;case 1:if(!c(a,'')){return false}break;case 2:if(!c(a,'lös')){return false}break;case 3:if(!c(a,'full')){return false}break}a.A=d;return true};b.prototype.H=function(){var g;var f;var h;var b;var c;var a;var d;var i;var j;var k;var l;var e;g=this._;b=true;a:while(b===true){b=false;if(!D(this)){break a}}i=this._=g;this.A=i;k=this._=j=this.B;f=j-k;c=true;a:while(c===true){c=false;if(!w(this)){break a}}e=this._=(l=this.B)-f;h=l-e;a=true;a:while(a===true){a=false;if(!s(this)){break a}}this._=this.B-h;d=true;a:while(d===true){d=false;if(!q(this)){break a}}this._=this.A;return true};b.prototype.stem=b.prototype.H;b.prototype.L=function(a){return a instanceof b};b.prototype.equals=b.prototype.L;b.prototype.M=function(){var c;var a;var b;var d;c='SwedishStemmer';a=0;for(b=0;b<c.length;b++){d=c.charCodeAt(b);a=(a<<5)-a+d;a=a&a}return a|0};b.prototype.hashCode=b.prototype.M;b.serialVersionUID=1;h(b,'methodObject',function(){return new b});h(b,'a_0',function(){return[new a('a',-1,1),new a('arna',0,1),new a('erna',0,1),new a('heterna',2,1),new a('orna',0,1),new a('ad',-1,1),new a('e',-1,1),new a('ade',6,1),new a('ande',6,1),new a('arne',6,1),new a('are',6,1),new a('aste',6,1),new a('en',-1,1),new a('anden',12,1),new a('aren',12,1),new a('heten',12,1),new a('ern',-1,1),new a('ar',-1,1),new a('er',-1,1),new a('heter',18,1),new a('or',-1,1),new a('s',-1,2),new a('as',21,1),new a('arnas',22,1),new a('ernas',22,1),new a('ornas',22,1),new a('es',21,1),new a('ades',26,1),new a('andes',26,1),new a('ens',21,1),new a('arens',29,1),new a('hetens',29,1),new a('erns',21,1),new a('at',-1,1),new a('andet',-1,1),new a('het',-1,1),new a('ast',-1,1)]});h(b,'a_1',function(){return[new a('dd',-1,-1),new a('gd',-1,-1),new a('nn',-1,-1),new a('dt',-1,-1),new a('gt',-1,-1),new a('kt',-1,-1),new a('tt',-1,-1)]});h(b,'a_2',function(){return[new a('ig',-1,1),new a('lig',0,1),new a('els',-1,1),new a('fullt',-1,3),new a('löst',-1,2)]});h(b,'g_v',function(){return[17,65,16,1,0,0,0,0,0,0,0,0,0,0,0,0,24,0,32]});h(b,'g_s_ending',function(){return[119,127,149]});var n={'src/stemmer.jsx':{Stemmer:j},'src/swedish-stemmer.jsx':{SwedishStemmer:b}}}(JSX))
var Stemmer = JSX.require("src/swedish-stemmer.jsx").SwedishStemmer;
"""


class SearchSwedish(SearchLanguage):
    lang = 'sv'
    language_name = 'Swedish'
    js_stemmer_rawcode = 'swedish-stemmer.js'
    js_stemmer_code = js_stemmer
    stopwords = swedish_stopwords

    def init(self, options):
        # type: (Any) -> None
        self.stemmer = snowballstemmer.stemmer('swedish')

    def stem(self, word):
        # type: (unicode) -> unicode
        return self.stemmer.stemWord(word.lower())
