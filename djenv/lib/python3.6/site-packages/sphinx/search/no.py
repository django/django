# -*- coding: utf-8 -*-
"""
    sphinx.search.no
    ~~~~~~~~~~~~~~~~

    Norwegian search language: includes the JS Norwegian stemmer.

    :copyright: Copyright 2007-2013 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from sphinx.search import SearchLanguage, parse_stop_word

import snowballstemmer

if False:
    # For type annotation
    from typing import Any  # NOQA


norwegian_stopwords = parse_stop_word(u'''
| source: http://snowball.tartarus.org/algorithms/norwegian/stop.txt
og             | and
i              | in
jeg            | I
det            | it/this/that
at             | to (w. inf.)
en             | a/an
et             | a/an
den            | it/this/that
til            | to
er             | is/am/are
som            | who/that
på             | on
de             | they / you(formal)
med            | with
han            | he
av             | of
ikke           | not
ikkje          | not *
der            | there
så             | so
var            | was/were
meg            | me
seg            | you
men            | but
ett            | one
har            | have
om             | about
vi             | we
min            | my
mitt           | my
ha             | have
hadde          | had
hun            | she
nå             | now
over           | over
da             | when/as
ved            | by/know
fra            | from
du             | you
ut             | out
sin            | your
dem            | them
oss            | us
opp            | up
man            | you/one
kan            | can
hans           | his
hvor           | where
eller          | or
hva            | what
skal           | shall/must
selv           | self (reflective)
sjøl           | self (reflective)
her            | here
alle           | all
vil            | will
bli            | become
ble            | became
blei           | became *
blitt          | have become
kunne          | could
inn            | in
når            | when
være           | be
kom            | come
noen           | some
noe            | some
ville          | would
dere           | you
som            | who/which/that
deres          | their/theirs
kun            | only/just
ja             | yes
etter          | after
ned            | down
skulle         | should
denne          | this
for            | for/because
deg            | you
si             | hers/his
sine           | hers/his
sitt           | hers/his
mot            | against
å              | to
meget          | much
hvorfor        | why
dette          | this
disse          | these/those
uten           | without
hvordan        | how
ingen          | none
din            | your
ditt           | your
blir           | become
samme          | same
hvilken        | which
hvilke         | which (plural)
sånn           | such a
inni           | inside/within
mellom         | between
vår            | our
hver           | each
hvem           | who
vors           | us/ours
hvis           | whose
både           | both
bare           | only/just
enn            | than
fordi          | as/because
før            | before
mange          | many
også           | also
slik           | just
vært           | been
være           | to be
båe            | both *
begge          | both
siden          | since
dykk           | your *
dykkar         | yours *
dei            | they *
deira          | them *
deires         | theirs *
deim           | them *
di             | your (fem.) *
då             | as/when *
eg             | I *
ein            | a/an *
eit            | a/an *
eitt           | a/an *
elles          | or *
honom          | he *
hjå            | at *
ho             | she *
hoe            | she *
henne          | her
hennar         | her/hers
hennes         | hers
hoss           | how *
hossen         | how *
ikkje          | not *
ingi           | noone *
inkje          | noone *
korleis        | how *
korso          | how *
kva            | what/which *
kvar           | where *
kvarhelst      | where *
kven           | who/whom *
kvi            | why *
kvifor         | why *
me             | we *
medan          | while *
mi             | my *
mine           | my *
mykje          | much *
no             | now *
nokon          | some (masc./neut.) *
noka           | some (fem.) *
nokor          | some *
noko           | some *
nokre          | some *
si             | his/hers *
sia            | since *
sidan          | since *
so             | so *
somt           | some *
somme          | some *
um             | about*
upp            | up *
vere           | be *
vore           | was *
verte          | become *
vort           | become *
varte          | became *
vart           | became *
''')

js_stemmer = u"""
var JSX={};(function(g){function i(b,e){var a=function(){};a.prototype=e.prototype;var c=new a;for(var d in b){b[d].prototype=c}}function G(c,b){for(var a in b.prototype)if(b.prototype.hasOwnProperty(a))c.prototype[a]=b.prototype[a]}function e(a,b,d){function c(a,b,c){delete a[b];a[b]=c;return c}Object.defineProperty(a,b,{get:function(){return c(a,b,d())},set:function(d){c(a,b,d)},enumerable:true,configurable:true})}function H(a,b,c){return a[b]=a[b]/c|0}var B=parseInt;var q=parseFloat;function I(a){return a!==a}var y=isFinite;var x=encodeURIComponent;var w=decodeURIComponent;var u=encodeURI;var t=decodeURI;var s=Object.prototype.toString;var r=Object.prototype.hasOwnProperty;function h(){}g.require=function(b){var a=m[b];return a!==undefined?a:null};g.profilerIsRunning=function(){return h.getResults!=null};g.getProfileResults=function(){return(h.getResults||function(){return{}})()};g.postProfileResults=function(a,b){if(h.postResults==null)throw new Error('profiler has not been turned on');return h.postResults(a,b)};g.resetProfileResults=function(){if(h.resetResults==null)throw new Error('profiler has not been turned on');return h.resetResults()};g.DEBUG=false;function A(){};i([A],Error);function b(a,b,c){this.G=a.length;this.R=a;this.U=b;this.J=c;this.I=null;this.V=null};i([b],Object);function j(){};i([j],Object);function d(){var a;var b;var c;this.F={};a=this.C='';b=this._=0;c=this.A=a.length;this.B=0;this.D=b;this.E=c};i([d],j);function v(a,b){a.C=b.C;a._=b._;a.A=b.A;a.B=b.B;a.D=b.D;a.E=b.E};function l(b,d,c,e){var a;if(b._>=b.A){return false}a=b.C.charCodeAt(b._);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._++;return true};function k(b,d,c,e){var a;if(b._<=b.B){return false}a=b.C.charCodeAt(b._-1);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._--;return true};function p(a,d,c,e){var b;if(a._>=a.A){return false}b=a.C.charCodeAt(a._);if(b>e||b<c){a._++;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._++;return true}return false};function o(a,d,c,e){var b;if(a._<=a.B){return false}b=a.C.charCodeAt(a._-1);if(b>e||b<c){a._--;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._--;return true}return false};function n(a,b,d){var c;if(a._-a.B<b){return false}if(a.C.slice((c=a._)-b,c)!==d){return false}a._-=b;return true};function f(d,m,p){var b;var g;var e;var n;var f;var k;var l;var i;var h;var c;var a;var j;var o;b=0;g=p;e=d._;n=d.B;f=0;k=0;l=false;while(true){i=b+(g-b>>1);h=0;c=f<k?f:k;a=m[i];for(j=a.G-1-c;j>=0;j--){if(e-c===n){h=-1;break}h=d.C.charCodeAt(e-1-c)-a.R.charCodeAt(j);if(h!==0){break}c++}if(h<0){g=i;k=c}else{b=i;f=c}if(g-b<=1){if(b>0){break}if(g===b){break}if(l){break}l=true}}while(true){a=m[b];if(f>=a.G){d._=e-a.G|0;if(a.I==null){return a.J}o=a.I(d);d._=e-a.G|0;if(o){return a.J}}b=a.U;if(b<0){return 0}}return-1};function C(a,b,d,e){var c;c=e.length-(d-b);a.C=a.C.slice(0,b)+e+a.C.slice(d);a.A+=c|0;if(a._>=d){a._+=c|0}else if(a._>b){a._=b}return c|0};function c(a,f){var b;var c;var d;var e;b=false;if((c=a.D)<0||c>(d=a.E)||d>(e=a.A)||e>a.C.length?false:true){C(a,a.D,a.E,f);b=true}return b};d.prototype.H=function(){return false};d.prototype.S=function(b){var a;var c;var d;var e;a=this.F['.'+b];if(a==null){c=this.C=b;d=this._=0;e=this.A=c.length;this.B=0;this.D=d;this.E=e;this.H();a=this.C;this.F['.'+b]=a}return a};d.prototype.stemWord=d.prototype.S;d.prototype.T=function(e){var d;var b;var c;var a;var f;var g;var h;d=[];for(b=0;b<e.length;b++){c=e[b];a=this.F['.'+c];if(a==null){f=this.C=c;g=this._=0;h=this.A=f.length;this.B=0;this.D=g;this.E=h;this.H();a=this.C;this.F['.'+c]=a}d.push(a)}return d};d.prototype.stemWords=d.prototype.T;function a(){d.call(this);this.I_x=0;this.I_p1=0};i([a],d);a.prototype.K=function(a){this.I_x=a.I_x;this.I_p1=a.I_p1;v(this,a)};a.prototype.copy_from=a.prototype.K;a.prototype.P=function(){var g;var d;var b;var e;var c;var f;var i;var j;var k;var h;this.I_p1=j=this.A;g=i=this._;b=i+3|0;if(0>b||b>j){return false}h=this._=b;this.I_x=h;this._=g;a:while(true){d=this._;e=true;b:while(e===true){e=false;if(!l(this,a.g_v,97,248)){break b}this._=d;break a}k=this._=d;if(k>=this.A){return false}this._++}a:while(true){c=true;b:while(c===true){c=false;if(!p(this,a.g_v,97,248)){break b}break a}if(this._>=this.A){return false}this._++}this.I_p1=this._;f=true;a:while(f===true){f=false;if(!(this.I_p1<this.I_x)){break a}this.I_p1=this.I_x}return true};a.prototype.r_mark_regions=a.prototype.P;function F(b){var h;var e;var c;var f;var d;var g;var j;var k;var m;var i;b.I_p1=k=b.A;h=j=b._;c=j+3|0;if(0>c||c>k){return false}i=b._=c;b.I_x=i;b._=h;a:while(true){e=b._;f=true;b:while(f===true){f=false;if(!l(b,a.g_v,97,248)){break b}b._=e;break a}m=b._=e;if(m>=b.A){return false}b._++}a:while(true){d=true;b:while(d===true){d=false;if(!p(b,a.g_v,97,248)){break b}break a}if(b._>=b.A){return false}b._++}b.I_p1=b._;g=true;a:while(g===true){g=false;if(!(b.I_p1<b.I_x)){break a}b.I_p1=b.I_x}return true};a.prototype.O=function(){var b;var h;var d;var i;var e;var g;var j;var l;var m;h=this.A-(j=this._);if(j<this.I_p1){return false}l=this._=this.I_p1;d=this.B;this.B=l;m=this._=this.A-h;this.E=m;b=f(this,a.a_0,29);if(b===0){this.B=d;return false}this.D=this._;this.B=d;switch(b){case 0:return false;case 1:if(!c(this,'')){return false}break;case 2:e=true;a:while(e===true){e=false;i=this.A-this._;g=true;b:while(g===true){g=false;if(!k(this,a.g_s_ending,98,122)){break b}break a}this._=this.A-i;if(!n(this,1,'k')){return false}if(!o(this,a.g_v,97,248)){return false}}if(!c(this,'')){return false}break;case 3:if(!c(this,'er')){return false}break}return true};a.prototype.r_main_suffix=a.prototype.O;function E(b){var d;var l;var e;var i;var g;var h;var m;var p;var j;l=b.A-(m=b._);if(m<b.I_p1){return false}p=b._=b.I_p1;e=b.B;b.B=p;j=b._=b.A-l;b.E=j;d=f(b,a.a_0,29);if(d===0){b.B=e;return false}b.D=b._;b.B=e;switch(d){case 0:return false;case 1:if(!c(b,'')){return false}break;case 2:g=true;a:while(g===true){g=false;i=b.A-b._;h=true;b:while(h===true){h=false;if(!k(b,a.g_s_ending,98,122)){break b}break a}b._=b.A-i;if(!n(b,1,'k')){return false}if(!o(b,a.g_v,97,248)){return false}}if(!c(b,'')){return false}break;case 3:if(!c(b,'er')){return false}break}return true};a.prototype.N=function(){var e;var g;var b;var h;var d;var i;var j;var k;var l;e=(h=this.A)-(d=this._);g=h-d;if(d<this.I_p1){return false}i=this._=this.I_p1;b=this.B;this.B=i;j=this._=this.A-g;this.E=j;if(f(this,a.a_1,2)===0){this.B=b;return false}this.D=this._;l=this.B=b;k=this._=this.A-e;if(k<=l){return false}this._--;this.D=this._;return!c(this,'')?false:true};a.prototype.r_consonant_pair=a.prototype.N;function D(b){var i;var j;var d;var g;var e;var k;var l;var m;var h;i=(g=b.A)-(e=b._);j=g-e;if(e<b.I_p1){return false}k=b._=b.I_p1;d=b.B;b.B=k;l=b._=b.A-j;b.E=l;if(f(b,a.a_1,2)===0){b.B=d;return false}b.D=b._;h=b.B=d;m=b._=b.A-i;if(m<=h){return false}b._--;b.D=b._;return!c(b,'')?false:true};a.prototype.Q=function(){var b;var e;var d;var g;var h;var i;e=this.A-(g=this._);if(g<this.I_p1){return false}h=this._=this.I_p1;d=this.B;this.B=h;i=this._=this.A-e;this.E=i;b=f(this,a.a_2,11);if(b===0){this.B=d;return false}this.D=this._;this.B=d;switch(b){case 0:return false;case 1:if(!c(this,'')){return false}break}return true};a.prototype.r_other_suffix=a.prototype.Q;function z(b){var d;var g;var e;var h;var i;var j;g=b.A-(h=b._);if(h<b.I_p1){return false}i=b._=b.I_p1;e=b.B;b.B=i;j=b._=b.A-g;b.E=j;d=f(b,a.a_2,11);if(d===0){b.B=e;return false}b.D=b._;b.B=e;switch(d){case 0:return false;case 1:if(!c(b,'')){return false}break}return true};a.prototype.H=function(){var g;var f;var h;var b;var c;var a;var d;var i;var j;var k;var l;var e;g=this._;b=true;a:while(b===true){b=false;if(!F(this)){break a}}i=this._=g;this.B=i;k=this._=j=this.A;f=j-k;c=true;a:while(c===true){c=false;if(!E(this)){break a}}e=this._=(l=this.A)-f;h=l-e;a=true;a:while(a===true){a=false;if(!D(this)){break a}}this._=this.A-h;d=true;a:while(d===true){d=false;if(!z(this)){break a}}this._=this.B;return true};a.prototype.stem=a.prototype.H;a.prototype.L=function(b){return b instanceof a};a.prototype.equals=a.prototype.L;a.prototype.M=function(){var c;var a;var b;var d;c='NorwegianStemmer';a=0;for(b=0;b<c.length;b++){d=c.charCodeAt(b);a=(a<<5)-a+d;a=a&a}return a|0};a.prototype.hashCode=a.prototype.M;a.serialVersionUID=1;e(a,'methodObject',function(){return new a});e(a,'a_0',function(){return[new b('a',-1,1),new b('e',-1,1),new b('ede',1,1),new b('ande',1,1),new b('ende',1,1),new b('ane',1,1),new b('ene',1,1),new b('hetene',6,1),new b('erte',1,3),new b('en',-1,1),new b('heten',9,1),new b('ar',-1,1),new b('er',-1,1),new b('heter',12,1),new b('s',-1,2),new b('as',14,1),new b('es',14,1),new b('edes',16,1),new b('endes',16,1),new b('enes',16,1),new b('hetenes',19,1),new b('ens',14,1),new b('hetens',21,1),new b('ers',14,1),new b('ets',14,1),new b('et',-1,1),new b('het',25,1),new b('ert',-1,3),new b('ast',-1,1)]});e(a,'a_1',function(){return[new b('dt',-1,-1),new b('vt',-1,-1)]});e(a,'a_2',function(){return[new b('leg',-1,1),new b('eleg',0,1),new b('ig',-1,1),new b('eig',2,1),new b('lig',2,1),new b('elig',4,1),new b('els',-1,1),new b('lov',-1,1),new b('elov',7,1),new b('slov',7,1),new b('hetslov',9,1)]});e(a,'g_v',function(){return[17,65,16,1,0,0,0,0,0,0,0,0,0,0,0,0,48,0,128]});e(a,'g_s_ending',function(){return[119,125,149,1]});var m={'src/stemmer.jsx':{Stemmer:j},'src/norwegian-stemmer.jsx':{NorwegianStemmer:a}}}(JSX))
var Stemmer = JSX.require("src/norwegian-stemmer.jsx").NorwegianStemmer;
"""


class SearchNorwegian(SearchLanguage):
    lang = 'no'
    language_name = 'Norwegian'
    js_stemmer_rawcode = 'norwegian-stemmer.js'
    js_stemmer_code = js_stemmer
    stopwords = norwegian_stopwords

    def init(self, options):
        # type: (Any) -> None
        self.stemmer = snowballstemmer.stemmer('norwegian')

    def stem(self, word):
        # type: (unicode) -> unicode
        return self.stemmer.stemWord(word.lower())
