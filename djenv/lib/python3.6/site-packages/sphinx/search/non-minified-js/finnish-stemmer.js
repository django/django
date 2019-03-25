// generatedy by JSX compiler 0.9.89 (2014-05-20 06:01:03 +0900; 8e8c6105f36f3dfe440ea026a3c93a3444977102)
var JSX = {};
(function (JSX) {
/**
 * extends the class
 */
function $__jsx_extend(derivations, base) {
	var ctor = function () {};
	ctor.prototype = base.prototype;
	var proto = new ctor();
	for (var i in derivations) {
		derivations[i].prototype = proto;
	}
}

/**
 * copies the implementations from source interface to target
 */
function $__jsx_merge_interface(target, source) {
	for (var k in source.prototype)
		if (source.prototype.hasOwnProperty(k))
			target.prototype[k] = source.prototype[k];
}

/**
 * defers the initialization of the property
 */
function $__jsx_lazy_init(obj, prop, func) {
	function reset(obj, prop, value) {
		delete obj[prop];
		obj[prop] = value;
		return value;
	}

	Object.defineProperty(obj, prop, {
		get: function () {
			return reset(obj, prop, func());
		},
		set: function (v) {
			reset(obj, prop, v);
		},
		enumerable: true,
		configurable: true
	});
}

var $__jsx_imul = Math.imul;
if (typeof $__jsx_imul === "undefined") {
	$__jsx_imul = function (a, b) {
		var ah  = (a >>> 16) & 0xffff;
		var al = a & 0xffff;
		var bh  = (b >>> 16) & 0xffff;
		var bl = b & 0xffff;
		return ((al * bl) + (((ah * bl + al * bh) << 16) >>> 0)|0);
	};
}

/**
 * fused int-ops with side-effects
 */
function $__jsx_ipadd(o, p, r) {
	return o[p] = (o[p] + r) | 0;
}
function $__jsx_ipsub(o, p, r) {
	return o[p] = (o[p] - r) | 0;
}
function $__jsx_ipmul(o, p, r) {
	return o[p] = $__jsx_imul(o[p], r);
}
function $__jsx_ipdiv(o, p, r) {
	return o[p] = (o[p] / r) | 0;
}
function $__jsx_ipmod(o, p, r) {
	return o[p] = (o[p] % r) | 0;
}
function $__jsx_ippostinc(o, p) {
	var v = o[p];
	o[p] = (v + 1) | 0;
	return v;
}
function $__jsx_ippostdec(o, p) {
	var v = o[p];
	o[p] = (v - 1) | 0;
	return v;
}

/**
 * non-inlined version of Array#each
 */
function $__jsx_forEach(o, f) {
	var l = o.length;
	for (var i = 0; i < l; ++i)
		f(o[i]);
}

/*
 * global functions, renamed to avoid conflict with local variable names
 */
var $__jsx_parseInt = parseInt;
var $__jsx_parseFloat = parseFloat;
function $__jsx_isNaN(n) { return n !== n; }
var $__jsx_isFinite = isFinite;

var $__jsx_encodeURIComponent = encodeURIComponent;
var $__jsx_decodeURIComponent = decodeURIComponent;
var $__jsx_encodeURI = encodeURI;
var $__jsx_decodeURI = decodeURI;

var $__jsx_ObjectToString = Object.prototype.toString;
var $__jsx_ObjectHasOwnProperty = Object.prototype.hasOwnProperty;

/*
 * profiler object, initialized afterwards
 */
function $__jsx_profiler() {
}

/*
 * public interface to JSX code
 */
JSX.require = function (path) {
	var m = $__jsx_classMap[path];
	return m !== undefined ? m : null;
};

JSX.profilerIsRunning = function () {
	return $__jsx_profiler.getResults != null;
};

JSX.getProfileResults = function () {
	return ($__jsx_profiler.getResults || function () { return {}; })();
};

JSX.postProfileResults = function (url, cb) {
	if ($__jsx_profiler.postResults == null)
		throw new Error("profiler has not been turned on");
	return $__jsx_profiler.postResults(url, cb);
};

JSX.resetProfileResults = function () {
	if ($__jsx_profiler.resetResults == null)
		throw new Error("profiler has not been turned on");
	return $__jsx_profiler.resetResults();
};
JSX.DEBUG = false;
var GeneratorFunction$0 = 
(function () {
  try {
    return Function('import {GeneratorFunction} from "std:iteration"; return GeneratorFunction')();
  } catch (e) {
    return function GeneratorFunction () {};
  }
})();
var __jsx_generator_object$0 = 
(function () {
  function __jsx_generator_object() {
  	this.__next = 0;
  	this.__loop = null;
	this.__seed = null;
  	this.__value = undefined;
  	this.__status = 0;	// SUSPENDED: 0, ACTIVE: 1, DEAD: 2
  }

  __jsx_generator_object.prototype.next = function (seed) {
  	switch (this.__status) {
  	case 0:
  		this.__status = 1;
  		this.__seed = seed;

  		// go next!
  		this.__loop(this.__next);

  		var done = false;
  		if (this.__next != -1) {
  			this.__status = 0;
  		} else {
  			this.__status = 2;
  			done = true;
  		}
  		return { value: this.__value, done: done };
  	case 1:
  		throw new Error("Generator is already running");
  	case 2:
  		throw new Error("Generator is already finished");
  	default:
  		throw new Error("Unexpected generator internal state");
  	}
  };

  return __jsx_generator_object;
}());
function Among(s, substring_i, result) {
	this.s_size = s.length;
	this.s = s;
	this.substring_i = substring_i;
	this.result = result;
	this.method = null;
	this.instance = null;
};

function Among$0(s, substring_i, result, method, instance) {
	this.s_size = s.length;
	this.s = s;
	this.substring_i = substring_i;
	this.result = result;
	this.method = method;
	this.instance = instance;
};

$__jsx_extend([Among, Among$0], Object);
function Stemmer() {
};

$__jsx_extend([Stemmer], Object);
function BaseStemmer() {
	var current$0;
	var cursor$0;
	var limit$0;
	this.cache = ({  });
	current$0 = this.current = "";
	cursor$0 = this.cursor = 0;
	limit$0 = this.limit = current$0.length;
	this.limit_backward = 0;
	this.bra = cursor$0;
	this.ket = limit$0;
};

$__jsx_extend([BaseStemmer], Stemmer);
BaseStemmer.prototype.setCurrent$S = function (value) {
	var current$0;
	var cursor$0;
	var limit$0;
	current$0 = this.current = value;
	cursor$0 = this.cursor = 0;
	limit$0 = this.limit = current$0.length;
	this.limit_backward = 0;
	this.bra = cursor$0;
	this.ket = limit$0;
};


function BaseStemmer$setCurrent$LBaseStemmer$S($this, value) {
	var current$0;
	var cursor$0;
	var limit$0;
	current$0 = $this.current = value;
	cursor$0 = $this.cursor = 0;
	limit$0 = $this.limit = current$0.length;
	$this.limit_backward = 0;
	$this.bra = cursor$0;
	$this.ket = limit$0;
};

BaseStemmer.setCurrent$LBaseStemmer$S = BaseStemmer$setCurrent$LBaseStemmer$S;

BaseStemmer.prototype.getCurrent$ = function () {
	return this.current;
};


function BaseStemmer$getCurrent$LBaseStemmer$($this) {
	return $this.current;
};

BaseStemmer.getCurrent$LBaseStemmer$ = BaseStemmer$getCurrent$LBaseStemmer$;

BaseStemmer.prototype.copy_from$LBaseStemmer$ = function (other) {
	this.current = other.current;
	this.cursor = other.cursor;
	this.limit = other.limit;
	this.limit_backward = other.limit_backward;
	this.bra = other.bra;
	this.ket = other.ket;
};


function BaseStemmer$copy_from$LBaseStemmer$LBaseStemmer$($this, other) {
	$this.current = other.current;
	$this.cursor = other.cursor;
	$this.limit = other.limit;
	$this.limit_backward = other.limit_backward;
	$this.bra = other.bra;
	$this.ket = other.ket;
};

BaseStemmer.copy_from$LBaseStemmer$LBaseStemmer$ = BaseStemmer$copy_from$LBaseStemmer$LBaseStemmer$;

BaseStemmer.prototype.in_grouping$AIII = function (s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor >= this.limit) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor);
	if (ch > max || ch < min) {
		return false;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$in_grouping$LBaseStemmer$AIII($this, s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor >= $this.limit) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor);
	if (ch > max || ch < min) {
		return false;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.in_grouping$LBaseStemmer$AIII = BaseStemmer$in_grouping$LBaseStemmer$AIII;

BaseStemmer.prototype.in_grouping_b$AIII = function (s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor <= this.limit_backward) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor - 1);
	if (ch > max || ch < min) {
		return false;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor <= $this.limit_backward) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor - 1);
	if (ch > max || ch < min) {
		return false;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.in_grouping_b$LBaseStemmer$AIII = BaseStemmer$in_grouping_b$LBaseStemmer$AIII;

BaseStemmer.prototype.out_grouping$AIII = function (s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor >= this.limit) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor);
	if (ch > max || ch < min) {
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		return true;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0X1 << (ch & 0x7)) === 0) {
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		return true;
	}
	return false;
};


function BaseStemmer$out_grouping$LBaseStemmer$AIII($this, s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor >= $this.limit) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor);
	if (ch > max || ch < min) {
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		return true;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0X1 << (ch & 0x7)) === 0) {
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		return true;
	}
	return false;
};

BaseStemmer.out_grouping$LBaseStemmer$AIII = BaseStemmer$out_grouping$LBaseStemmer$AIII;

BaseStemmer.prototype.out_grouping_b$AIII = function (s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor <= this.limit_backward) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor - 1);
	if (ch > max || ch < min) {
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		return true;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		return true;
	}
	return false;
};


function BaseStemmer$out_grouping_b$LBaseStemmer$AIII($this, s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor <= $this.limit_backward) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor - 1);
	if (ch > max || ch < min) {
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		return true;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		return true;
	}
	return false;
};

BaseStemmer.out_grouping_b$LBaseStemmer$AIII = BaseStemmer$out_grouping_b$LBaseStemmer$AIII;

BaseStemmer.prototype.in_range$II = function (min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor >= this.limit) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor);
	if (ch > max || ch < min) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$in_range$LBaseStemmer$II($this, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor >= $this.limit) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor);
	if (ch > max || ch < min) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.in_range$LBaseStemmer$II = BaseStemmer$in_range$LBaseStemmer$II;

BaseStemmer.prototype.in_range_b$II = function (min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor <= this.limit_backward) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor - 1);
	if (ch > max || ch < min) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$in_range_b$LBaseStemmer$II($this, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor <= $this.limit_backward) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor - 1);
	if (ch > max || ch < min) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.in_range_b$LBaseStemmer$II = BaseStemmer$in_range_b$LBaseStemmer$II;

BaseStemmer.prototype.out_range$II = function (min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor >= this.limit) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor);
	if (! (ch > max || ch < min)) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$out_range$LBaseStemmer$II($this, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor >= $this.limit) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor);
	if (! (ch > max || ch < min)) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.out_range$LBaseStemmer$II = BaseStemmer$out_range$LBaseStemmer$II;

BaseStemmer.prototype.out_range_b$II = function (min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor <= this.limit_backward) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor - 1);
	if (! (ch > max || ch < min)) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$out_range_b$LBaseStemmer$II($this, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor <= $this.limit_backward) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor - 1);
	if (! (ch > max || ch < min)) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.out_range_b$LBaseStemmer$II = BaseStemmer$out_range_b$LBaseStemmer$II;

BaseStemmer.prototype.eq_s$IS = function (s_size, s) {
	var cursor$0;
	if (((this.limit - this.cursor) | 0) < s_size) {
		return false;
	}
	if (this.current.slice(cursor$0 = this.cursor, ((cursor$0 + s_size) | 0)) !== s) {
		return false;
	}
	this.cursor = (this.cursor + s_size) | 0;
	return true;
};


function BaseStemmer$eq_s$LBaseStemmer$IS($this, s_size, s) {
	var cursor$0;
	if ((($this.limit - $this.cursor) | 0) < s_size) {
		return false;
	}
	if ($this.current.slice(cursor$0 = $this.cursor, ((cursor$0 + s_size) | 0)) !== s) {
		return false;
	}
	$this.cursor = ($this.cursor + s_size) | 0;
	return true;
};

BaseStemmer.eq_s$LBaseStemmer$IS = BaseStemmer$eq_s$LBaseStemmer$IS;

BaseStemmer.prototype.eq_s_b$IS = function (s_size, s) {
	var cursor$0;
	if (((this.cursor - this.limit_backward) | 0) < s_size) {
		return false;
	}
	if (this.current.slice((((cursor$0 = this.cursor) - s_size) | 0), cursor$0) !== s) {
		return false;
	}
	this.cursor = (this.cursor - s_size) | 0;
	return true;
};


function BaseStemmer$eq_s_b$LBaseStemmer$IS($this, s_size, s) {
	var cursor$0;
	if ((($this.cursor - $this.limit_backward) | 0) < s_size) {
		return false;
	}
	if ($this.current.slice((((cursor$0 = $this.cursor) - s_size) | 0), cursor$0) !== s) {
		return false;
	}
	$this.cursor = ($this.cursor - s_size) | 0;
	return true;
};

BaseStemmer.eq_s_b$LBaseStemmer$IS = BaseStemmer$eq_s_b$LBaseStemmer$IS;

BaseStemmer.prototype.eq_v$S = function (s) {
	return BaseStemmer$eq_s$LBaseStemmer$IS(this, s.length, s);
};


function BaseStemmer$eq_v$LBaseStemmer$S($this, s) {
	return BaseStemmer$eq_s$LBaseStemmer$IS($this, s.length, s);
};

BaseStemmer.eq_v$LBaseStemmer$S = BaseStemmer$eq_v$LBaseStemmer$S;

BaseStemmer.prototype.eq_v_b$S = function (s) {
	return BaseStemmer$eq_s_b$LBaseStemmer$IS(this, s.length, s);
};


function BaseStemmer$eq_v_b$LBaseStemmer$S($this, s) {
	return BaseStemmer$eq_s_b$LBaseStemmer$IS($this, s.length, s);
};

BaseStemmer.eq_v_b$LBaseStemmer$S = BaseStemmer$eq_v_b$LBaseStemmer$S;

BaseStemmer.prototype.find_among$ALAmong$I = function (v, v_size) {
	var i;
	var j;
	var c;
	var l;
	var common_i;
	var common_j;
	var first_key_inspected;
	var k;
	var diff;
	var common;
	var w;
	var i2;
	var res;
	i = 0;
	j = v_size;
	c = this.cursor;
	l = this.limit;
	common_i = 0;
	common_j = 0;
	first_key_inspected = false;
	while (true) {
		k = i + (j - i >>> 1);
		diff = 0;
		common = (common_i < common_j ? common_i : common_j);
		w = v[k];
		for (i2 = common; i2 < w.s_size; i2++) {
			if (c + common === l) {
				diff = -1;
				break;
			}
			diff = this.current.charCodeAt(c + common) - w.s.charCodeAt(i2);
			if (diff !== 0) {
				break;
			}
			common++;
		}
		if (diff < 0) {
			j = k;
			common_j = common;
		} else {
			i = k;
			common_i = common;
		}
		if (j - i <= 1) {
			if (i > 0) {
				break;
			}
			if (j === i) {
				break;
			}
			if (first_key_inspected) {
				break;
			}
			first_key_inspected = true;
		}
	}
	while (true) {
		w = v[i];
		if (common_i >= w.s_size) {
			this.cursor = (c + w.s_size | 0);
			if (w.method == null) {
				return w.result;
			}
			res = w.method(w.instance);
			this.cursor = (c + w.s_size | 0);
			if (res) {
				return w.result;
			}
		}
		i = w.substring_i;
		if (i < 0) {
			return 0;
		}
	}
	return -1;
};


function BaseStemmer$find_among$LBaseStemmer$ALAmong$I($this, v, v_size) {
	var i;
	var j;
	var c;
	var l;
	var common_i;
	var common_j;
	var first_key_inspected;
	var k;
	var diff;
	var common;
	var w;
	var i2;
	var res;
	i = 0;
	j = v_size;
	c = $this.cursor;
	l = $this.limit;
	common_i = 0;
	common_j = 0;
	first_key_inspected = false;
	while (true) {
		k = i + (j - i >>> 1);
		diff = 0;
		common = (common_i < common_j ? common_i : common_j);
		w = v[k];
		for (i2 = common; i2 < w.s_size; i2++) {
			if (c + common === l) {
				diff = -1;
				break;
			}
			diff = $this.current.charCodeAt(c + common) - w.s.charCodeAt(i2);
			if (diff !== 0) {
				break;
			}
			common++;
		}
		if (diff < 0) {
			j = k;
			common_j = common;
		} else {
			i = k;
			common_i = common;
		}
		if (j - i <= 1) {
			if (i > 0) {
				break;
			}
			if (j === i) {
				break;
			}
			if (first_key_inspected) {
				break;
			}
			first_key_inspected = true;
		}
	}
	while (true) {
		w = v[i];
		if (common_i >= w.s_size) {
			$this.cursor = (c + w.s_size | 0);
			if (w.method == null) {
				return w.result;
			}
			res = w.method(w.instance);
			$this.cursor = (c + w.s_size | 0);
			if (res) {
				return w.result;
			}
		}
		i = w.substring_i;
		if (i < 0) {
			return 0;
		}
	}
	return -1;
};

BaseStemmer.find_among$LBaseStemmer$ALAmong$I = BaseStemmer$find_among$LBaseStemmer$ALAmong$I;

BaseStemmer.prototype.find_among_b$ALAmong$I = function (v, v_size) {
	var i;
	var j;
	var c;
	var lb;
	var common_i;
	var common_j;
	var first_key_inspected;
	var k;
	var diff;
	var common;
	var w;
	var i2;
	var res;
	i = 0;
	j = v_size;
	c = this.cursor;
	lb = this.limit_backward;
	common_i = 0;
	common_j = 0;
	first_key_inspected = false;
	while (true) {
		k = i + (j - i >> 1);
		diff = 0;
		common = (common_i < common_j ? common_i : common_j);
		w = v[k];
		for (i2 = w.s_size - 1 - common; i2 >= 0; i2--) {
			if (c - common === lb) {
				diff = -1;
				break;
			}
			diff = this.current.charCodeAt(c - 1 - common) - w.s.charCodeAt(i2);
			if (diff !== 0) {
				break;
			}
			common++;
		}
		if (diff < 0) {
			j = k;
			common_j = common;
		} else {
			i = k;
			common_i = common;
		}
		if (j - i <= 1) {
			if (i > 0) {
				break;
			}
			if (j === i) {
				break;
			}
			if (first_key_inspected) {
				break;
			}
			first_key_inspected = true;
		}
	}
	while (true) {
		w = v[i];
		if (common_i >= w.s_size) {
			this.cursor = (c - w.s_size | 0);
			if (w.method == null) {
				return w.result;
			}
			res = w.method(this);
			this.cursor = (c - w.s_size | 0);
			if (res) {
				return w.result;
			}
		}
		i = w.substring_i;
		if (i < 0) {
			return 0;
		}
	}
	return -1;
};


function BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, v, v_size) {
	var i;
	var j;
	var c;
	var lb;
	var common_i;
	var common_j;
	var first_key_inspected;
	var k;
	var diff;
	var common;
	var w;
	var i2;
	var res;
	i = 0;
	j = v_size;
	c = $this.cursor;
	lb = $this.limit_backward;
	common_i = 0;
	common_j = 0;
	first_key_inspected = false;
	while (true) {
		k = i + (j - i >> 1);
		diff = 0;
		common = (common_i < common_j ? common_i : common_j);
		w = v[k];
		for (i2 = w.s_size - 1 - common; i2 >= 0; i2--) {
			if (c - common === lb) {
				diff = -1;
				break;
			}
			diff = $this.current.charCodeAt(c - 1 - common) - w.s.charCodeAt(i2);
			if (diff !== 0) {
				break;
			}
			common++;
		}
		if (diff < 0) {
			j = k;
			common_j = common;
		} else {
			i = k;
			common_i = common;
		}
		if (j - i <= 1) {
			if (i > 0) {
				break;
			}
			if (j === i) {
				break;
			}
			if (first_key_inspected) {
				break;
			}
			first_key_inspected = true;
		}
	}
	while (true) {
		w = v[i];
		if (common_i >= w.s_size) {
			$this.cursor = (c - w.s_size | 0);
			if (w.method == null) {
				return w.result;
			}
			res = w.method($this);
			$this.cursor = (c - w.s_size | 0);
			if (res) {
				return w.result;
			}
		}
		i = w.substring_i;
		if (i < 0) {
			return 0;
		}
	}
	return -1;
};

BaseStemmer.find_among_b$LBaseStemmer$ALAmong$I = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I;

BaseStemmer.prototype.replace_s$IIS = function (c_bra, c_ket, s) {
	var adjustment;
	adjustment = ((s.length - (((c_ket - c_bra) | 0))) | 0);
	this.current = this.current.slice(0, c_bra) + s + this.current.slice(c_ket);
	this.limit = (this.limit + adjustment) | 0;
	if (this.cursor >= c_ket) {
		this.cursor = (this.cursor + adjustment) | 0;
	} else if (this.cursor > c_bra) {
		this.cursor = c_bra;
	}
	return (adjustment | 0);
};


function BaseStemmer$replace_s$LBaseStemmer$IIS($this, c_bra, c_ket, s) {
	var adjustment;
	adjustment = ((s.length - (((c_ket - c_bra) | 0))) | 0);
	$this.current = $this.current.slice(0, c_bra) + s + $this.current.slice(c_ket);
	$this.limit = ($this.limit + adjustment) | 0;
	if ($this.cursor >= c_ket) {
		$this.cursor = ($this.cursor + adjustment) | 0;
	} else if ($this.cursor > c_bra) {
		$this.cursor = c_bra;
	}
	return (adjustment | 0);
};

BaseStemmer.replace_s$LBaseStemmer$IIS = BaseStemmer$replace_s$LBaseStemmer$IIS;

BaseStemmer.prototype.slice_check$ = function () {
	var bra$0;
	var ket$0;
	var limit$0;
	return ((bra$0 = this.bra) < 0 || bra$0 > (ket$0 = this.ket) || ket$0 > (limit$0 = this.limit) || limit$0 > this.current.length ? false : true);
};


function BaseStemmer$slice_check$LBaseStemmer$($this) {
	var bra$0;
	var ket$0;
	var limit$0;
	return ((bra$0 = $this.bra) < 0 || bra$0 > (ket$0 = $this.ket) || ket$0 > (limit$0 = $this.limit) || limit$0 > $this.current.length ? false : true);
};

BaseStemmer.slice_check$LBaseStemmer$ = BaseStemmer$slice_check$LBaseStemmer$;

BaseStemmer.prototype.slice_from$S = function (s) {
	var result;
	var bra$0;
	var ket$0;
	var limit$0;
	result = false;
	if ((bra$0 = this.bra) < 0 || bra$0 > (ket$0 = this.ket) || ket$0 > (limit$0 = this.limit) || limit$0 > this.current.length ? false : true) {
		BaseStemmer$replace_s$LBaseStemmer$IIS(this, this.bra, this.ket, s);
		result = true;
	}
	return result;
};


function BaseStemmer$slice_from$LBaseStemmer$S($this, s) {
	var result;
	var bra$0;
	var ket$0;
	var limit$0;
	result = false;
	if ((bra$0 = $this.bra) < 0 || bra$0 > (ket$0 = $this.ket) || ket$0 > (limit$0 = $this.limit) || limit$0 > $this.current.length ? false : true) {
		BaseStemmer$replace_s$LBaseStemmer$IIS($this, $this.bra, $this.ket, s);
		result = true;
	}
	return result;
};

BaseStemmer.slice_from$LBaseStemmer$S = BaseStemmer$slice_from$LBaseStemmer$S;

BaseStemmer.prototype.slice_del$ = function () {
	return BaseStemmer$slice_from$LBaseStemmer$S(this, "");
};


function BaseStemmer$slice_del$LBaseStemmer$($this) {
	return BaseStemmer$slice_from$LBaseStemmer$S($this, "");
};

BaseStemmer.slice_del$LBaseStemmer$ = BaseStemmer$slice_del$LBaseStemmer$;

BaseStemmer.prototype.insert$IIS = function (c_bra, c_ket, s) {
	var adjustment;
	adjustment = BaseStemmer$replace_s$LBaseStemmer$IIS(this, c_bra, c_ket, s);
	if (c_bra <= this.bra) {
		this.bra = (this.bra + adjustment) | 0;
	}
	if (c_bra <= this.ket) {
		this.ket = (this.ket + adjustment) | 0;
	}
};


function BaseStemmer$insert$LBaseStemmer$IIS($this, c_bra, c_ket, s) {
	var adjustment;
	adjustment = BaseStemmer$replace_s$LBaseStemmer$IIS($this, c_bra, c_ket, s);
	if (c_bra <= $this.bra) {
		$this.bra = ($this.bra + adjustment) | 0;
	}
	if (c_bra <= $this.ket) {
		$this.ket = ($this.ket + adjustment) | 0;
	}
};

BaseStemmer.insert$LBaseStemmer$IIS = BaseStemmer$insert$LBaseStemmer$IIS;

BaseStemmer.prototype.slice_to$S = function (s) {
	var result;
	var bra$0;
	var ket$0;
	var limit$0;
	result = '';
	if ((bra$0 = this.bra) < 0 || bra$0 > (ket$0 = this.ket) || ket$0 > (limit$0 = this.limit) || limit$0 > this.current.length ? false : true) {
		result = this.current.slice(this.bra, this.ket);
	}
	return result;
};


function BaseStemmer$slice_to$LBaseStemmer$S($this, s) {
	var result;
	var bra$0;
	var ket$0;
	var limit$0;
	result = '';
	if ((bra$0 = $this.bra) < 0 || bra$0 > (ket$0 = $this.ket) || ket$0 > (limit$0 = $this.limit) || limit$0 > $this.current.length ? false : true) {
		result = $this.current.slice($this.bra, $this.ket);
	}
	return result;
};

BaseStemmer.slice_to$LBaseStemmer$S = BaseStemmer$slice_to$LBaseStemmer$S;

BaseStemmer.prototype.assign_to$S = function (s) {
	return this.current.slice(0, this.limit);
};


function BaseStemmer$assign_to$LBaseStemmer$S($this, s) {
	return $this.current.slice(0, $this.limit);
};

BaseStemmer.assign_to$LBaseStemmer$S = BaseStemmer$assign_to$LBaseStemmer$S;

BaseStemmer.prototype.stem$ = function () {
	return false;
};


BaseStemmer.prototype.stemWord$S = function (word) {
	var result;
	var current$0;
	var cursor$0;
	var limit$0;
	result = this.cache['.' + word];
	if (result == null) {
		current$0 = this.current = word;
		cursor$0 = this.cursor = 0;
		limit$0 = this.limit = current$0.length;
		this.limit_backward = 0;
		this.bra = cursor$0;
		this.ket = limit$0;
		this.stem$();
		result = this.current;
		this.cache['.' + word] = result;
	}
	return result;
};

BaseStemmer.prototype.stemWord = BaseStemmer.prototype.stemWord$S;

BaseStemmer.prototype.stemWords$AS = function (words) {
	var results;
	var i;
	var word;
	var result;
	var current$0;
	var cursor$0;
	var limit$0;
	results = [  ];
	for (i = 0; i < words.length; i++) {
		word = words[i];
		result = this.cache['.' + word];
		if (result == null) {
			current$0 = this.current = word;
			cursor$0 = this.cursor = 0;
			limit$0 = this.limit = current$0.length;
			this.limit_backward = 0;
			this.bra = cursor$0;
			this.ket = limit$0;
			this.stem$();
			result = this.current;
			this.cache['.' + word] = result;
		}
		results.push(result);
	}
	return results;
};

BaseStemmer.prototype.stemWords = BaseStemmer.prototype.stemWords$AS;

function FinnishStemmer() {
	BaseStemmer.call(this);
	this.B_ending_removed = false;
	this.S_x = "";
	this.I_p2 = 0;
	this.I_p1 = 0;
};

$__jsx_extend([FinnishStemmer], BaseStemmer);
FinnishStemmer.prototype.copy_from$LFinnishStemmer$ = function (other) {
	this.B_ending_removed = other.B_ending_removed;
	this.S_x = other.S_x;
	this.I_p2 = other.I_p2;
	this.I_p1 = other.I_p1;
	BaseStemmer$copy_from$LBaseStemmer$LBaseStemmer$(this, other);
};

FinnishStemmer.prototype.copy_from = FinnishStemmer.prototype.copy_from$LFinnishStemmer$;

FinnishStemmer.prototype.r_mark_regions$ = function () {
	var v_1;
	var v_3;
	var lab1;
	var lab3;
	var lab5;
	var lab7;
	var cursor$0;
	var limit$0;
	var cursor$1;
	var $__jsx_postinc_t;
	this.I_p1 = limit$0 = this.limit;
	this.I_p2 = limit$0;
golab0:
	while (true) {
		v_1 = this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, FinnishStemmer.g_V1, 97, 246)) {
				break lab1;
			}
			this.cursor = v_1;
			break golab0;
		}
		cursor$0 = this.cursor = v_1;
		if (cursor$0 >= this.limit) {
			return false;
		}
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	}
golab2:
	while (true) {
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, FinnishStemmer.g_V1, 97, 246)) {
				break lab3;
			}
			break golab2;
		}
		if (this.cursor >= this.limit) {
			return false;
		}
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	}
	this.I_p1 = this.cursor;
golab4:
	while (true) {
		v_3 = this.cursor;
		lab5 = true;
	lab5:
		while (lab5 === true) {
			lab5 = false;
			if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, FinnishStemmer.g_V1, 97, 246)) {
				break lab5;
			}
			this.cursor = v_3;
			break golab4;
		}
		cursor$1 = this.cursor = v_3;
		if (cursor$1 >= this.limit) {
			return false;
		}
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	}
golab6:
	while (true) {
		lab7 = true;
	lab7:
		while (lab7 === true) {
			lab7 = false;
			if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, FinnishStemmer.g_V1, 97, 246)) {
				break lab7;
			}
			break golab6;
		}
		if (this.cursor >= this.limit) {
			return false;
		}
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	}
	this.I_p2 = this.cursor;
	return true;
};

FinnishStemmer.prototype.r_mark_regions = FinnishStemmer.prototype.r_mark_regions$;

function FinnishStemmer$r_mark_regions$LFinnishStemmer$($this) {
	var v_1;
	var v_3;
	var lab1;
	var lab3;
	var lab5;
	var lab7;
	var cursor$0;
	var limit$0;
	var cursor$1;
	var $__jsx_postinc_t;
	$this.I_p1 = limit$0 = $this.limit;
	$this.I_p2 = limit$0;
golab0:
	while (true) {
		v_1 = $this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, FinnishStemmer.g_V1, 97, 246)) {
				break lab1;
			}
			$this.cursor = v_1;
			break golab0;
		}
		cursor$0 = $this.cursor = v_1;
		if (cursor$0 >= $this.limit) {
			return false;
		}
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	}
golab2:
	while (true) {
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, FinnishStemmer.g_V1, 97, 246)) {
				break lab3;
			}
			break golab2;
		}
		if ($this.cursor >= $this.limit) {
			return false;
		}
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	}
	$this.I_p1 = $this.cursor;
golab4:
	while (true) {
		v_3 = $this.cursor;
		lab5 = true;
	lab5:
		while (lab5 === true) {
			lab5 = false;
			if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, FinnishStemmer.g_V1, 97, 246)) {
				break lab5;
			}
			$this.cursor = v_3;
			break golab4;
		}
		cursor$1 = $this.cursor = v_3;
		if (cursor$1 >= $this.limit) {
			return false;
		}
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	}
golab6:
	while (true) {
		lab7 = true;
	lab7:
		while (lab7 === true) {
			lab7 = false;
			if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, FinnishStemmer.g_V1, 97, 246)) {
				break lab7;
			}
			break golab6;
		}
		if ($this.cursor >= $this.limit) {
			return false;
		}
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	}
	$this.I_p2 = $this.cursor;
	return true;
};

FinnishStemmer.r_mark_regions$LFinnishStemmer$ = FinnishStemmer$r_mark_regions$LFinnishStemmer$;

FinnishStemmer.prototype.r_R2$ = function () {
	return (! (this.I_p2 <= this.cursor) ? false : true);
};

FinnishStemmer.prototype.r_R2 = FinnishStemmer.prototype.r_R2$;

function FinnishStemmer$r_R2$LFinnishStemmer$($this) {
	return (! ($this.I_p2 <= $this.cursor) ? false : true);
};

FinnishStemmer.r_R2$LFinnishStemmer$ = FinnishStemmer$r_R2$LFinnishStemmer$;

FinnishStemmer.prototype.r_particle_etc$ = function () {
	var among_var;
	var v_1;
	var v_2;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	v_1 = ((this.limit - (cursor$0 = this.cursor)) | 0);
	if (cursor$0 < this.I_p1) {
		return false;
	}
	cursor$1 = this.cursor = this.I_p1;
	v_2 = this.limit_backward;
	this.limit_backward = cursor$1;
	cursor$2 = this.cursor = ((this.limit - v_1) | 0);
	this.ket = cursor$2;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FinnishStemmer.a_0, 10);
	if (among_var === 0) {
		this.limit_backward = v_2;
		return false;
	}
	this.bra = this.cursor;
	this.limit_backward = v_2;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, FinnishStemmer.g_particle_end, 97, 246)) {
			return false;
		}
		break;
	case 2:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			return false;
		}
		break;
	}
	return (! BaseStemmer$slice_from$LBaseStemmer$S(this, "") ? false : true);
};

FinnishStemmer.prototype.r_particle_etc = FinnishStemmer.prototype.r_particle_etc$;

function FinnishStemmer$r_particle_etc$LFinnishStemmer$($this) {
	var among_var;
	var v_1;
	var v_2;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	v_1 = (($this.limit - (cursor$0 = $this.cursor)) | 0);
	if (cursor$0 < $this.I_p1) {
		return false;
	}
	cursor$1 = $this.cursor = $this.I_p1;
	v_2 = $this.limit_backward;
	$this.limit_backward = cursor$1;
	cursor$2 = $this.cursor = (($this.limit - v_1) | 0);
	$this.ket = cursor$2;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FinnishStemmer.a_0, 10);
	if (among_var === 0) {
		$this.limit_backward = v_2;
		return false;
	}
	$this.bra = $this.cursor;
	$this.limit_backward = v_2;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, FinnishStemmer.g_particle_end, 97, 246)) {
			return false;
		}
		break;
	case 2:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			return false;
		}
		break;
	}
	return (! BaseStemmer$slice_from$LBaseStemmer$S($this, "") ? false : true);
};

FinnishStemmer.r_particle_etc$LFinnishStemmer$ = FinnishStemmer$r_particle_etc$LFinnishStemmer$;

FinnishStemmer.prototype.r_possessive$ = function () {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var lab0;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	v_1 = ((this.limit - (cursor$0 = this.cursor)) | 0);
	if (cursor$0 < this.I_p1) {
		return false;
	}
	cursor$1 = this.cursor = this.I_p1;
	v_2 = this.limit_backward;
	this.limit_backward = cursor$1;
	cursor$2 = this.cursor = ((this.limit - v_1) | 0);
	this.ket = cursor$2;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FinnishStemmer.a_4, 9);
	if (among_var === 0) {
		this.limit_backward = v_2;
		return false;
	}
	this.bra = this.cursor;
	this.limit_backward = v_2;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		v_3 = ((this.limit - this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "k")) {
				break lab0;
			}
			return false;
		}
		this.cursor = ((this.limit - v_3) | 0);
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		this.ket = this.cursor;
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 3, "kse")) {
			return false;
		}
		this.bra = this.cursor;
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ksi")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 4:
		if (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FinnishStemmer.a_1, 6) === 0) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 5:
		if (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FinnishStemmer.a_2, 6) === 0) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 6:
		if (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FinnishStemmer.a_3, 2) === 0) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	}
	return true;
};

FinnishStemmer.prototype.r_possessive = FinnishStemmer.prototype.r_possessive$;

function FinnishStemmer$r_possessive$LFinnishStemmer$($this) {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var lab0;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	v_1 = (($this.limit - (cursor$0 = $this.cursor)) | 0);
	if (cursor$0 < $this.I_p1) {
		return false;
	}
	cursor$1 = $this.cursor = $this.I_p1;
	v_2 = $this.limit_backward;
	$this.limit_backward = cursor$1;
	cursor$2 = $this.cursor = (($this.limit - v_1) | 0);
	$this.ket = cursor$2;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FinnishStemmer.a_4, 9);
	if (among_var === 0) {
		$this.limit_backward = v_2;
		return false;
	}
	$this.bra = $this.cursor;
	$this.limit_backward = v_2;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		v_3 = (($this.limit - $this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "k")) {
				break lab0;
			}
			return false;
		}
		$this.cursor = (($this.limit - v_3) | 0);
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		$this.ket = $this.cursor;
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 3, "kse")) {
			return false;
		}
		$this.bra = $this.cursor;
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ksi")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 4:
		if (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FinnishStemmer.a_1, 6) === 0) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 5:
		if (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FinnishStemmer.a_2, 6) === 0) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 6:
		if (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FinnishStemmer.a_3, 2) === 0) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	}
	return true;
};

FinnishStemmer.r_possessive$LFinnishStemmer$ = FinnishStemmer$r_possessive$LFinnishStemmer$;

FinnishStemmer.prototype.r_LONG$ = function () {
	return (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FinnishStemmer.a_5, 7) === 0 ? false : true);
};

FinnishStemmer.prototype.r_LONG = FinnishStemmer.prototype.r_LONG$;

function FinnishStemmer$r_LONG$LFinnishStemmer$($this) {
	return (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FinnishStemmer.a_5, 7) === 0 ? false : true);
};

FinnishStemmer.r_LONG$LFinnishStemmer$ = FinnishStemmer$r_LONG$LFinnishStemmer$;

FinnishStemmer.prototype.r_VI$ = function () {
	return (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "i") ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, FinnishStemmer.g_V2, 97, 246) ? false : true);
};

FinnishStemmer.prototype.r_VI = FinnishStemmer.prototype.r_VI$;

function FinnishStemmer$r_VI$LFinnishStemmer$($this) {
	return (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "i") ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, FinnishStemmer.g_V2, 97, 246) ? false : true);
};

FinnishStemmer.r_VI$LFinnishStemmer$ = FinnishStemmer$r_VI$LFinnishStemmer$;

FinnishStemmer.prototype.r_case_ending$ = function () {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var cursor$3;
	var $__jsx_postinc_t;
	v_1 = ((this.limit - (cursor$0 = this.cursor)) | 0);
	if (cursor$0 < this.I_p1) {
		return false;
	}
	cursor$1 = this.cursor = this.I_p1;
	v_2 = this.limit_backward;
	this.limit_backward = cursor$1;
	cursor$2 = this.cursor = ((this.limit - v_1) | 0);
	this.ket = cursor$2;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FinnishStemmer.a_6, 30);
	if (among_var === 0) {
		this.limit_backward = v_2;
		return false;
	}
	this.bra = this.cursor;
	this.limit_backward = v_2;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "a")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "e")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "i")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "o")) {
			return false;
		}
		break;
	case 5:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "\u00E4")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "\u00F6")) {
			return false;
		}
		break;
	case 7:
		v_3 = ((this.limit - this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			v_4 = ((this.limit - this.cursor) | 0);
			lab1 = true;
		lab1:
			while (lab1 === true) {
				lab1 = false;
				v_5 = ((this.limit - this.cursor) | 0);
				lab2 = true;
			lab2:
				while (lab2 === true) {
					lab2 = false;
					if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FinnishStemmer.a_5, 7) === 0 ? false : true)) {
						break lab2;
					}
					break lab1;
				}
				this.cursor = ((this.limit - v_5) | 0);
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 2, "ie")) {
					this.cursor = ((this.limit - v_3) | 0);
					break lab0;
				}
			}
			cursor$3 = this.cursor = ((this.limit - v_4) | 0);
			if (cursor$3 <= this.limit_backward) {
				this.cursor = ((this.limit - v_3) | 0);
				break lab0;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			this.bra = this.cursor;
		}
		break;
	case 8:
		if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, FinnishStemmer.g_V1, 97, 246)) {
			return false;
		}
		if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII(this, FinnishStemmer.g_V1, 97, 246)) {
			return false;
		}
		break;
	case 9:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "e")) {
			return false;
		}
		break;
	}
	if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
		return false;
	}
	this.B_ending_removed = true;
	return true;
};

FinnishStemmer.prototype.r_case_ending = FinnishStemmer.prototype.r_case_ending$;

function FinnishStemmer$r_case_ending$LFinnishStemmer$($this) {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var cursor$3;
	var $__jsx_postinc_t;
	v_1 = (($this.limit - (cursor$0 = $this.cursor)) | 0);
	if (cursor$0 < $this.I_p1) {
		return false;
	}
	cursor$1 = $this.cursor = $this.I_p1;
	v_2 = $this.limit_backward;
	$this.limit_backward = cursor$1;
	cursor$2 = $this.cursor = (($this.limit - v_1) | 0);
	$this.ket = cursor$2;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FinnishStemmer.a_6, 30);
	if (among_var === 0) {
		$this.limit_backward = v_2;
		return false;
	}
	$this.bra = $this.cursor;
	$this.limit_backward = v_2;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "a")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "e")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "i")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "o")) {
			return false;
		}
		break;
	case 5:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "\u00E4")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "\u00F6")) {
			return false;
		}
		break;
	case 7:
		v_3 = (($this.limit - $this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			v_4 = (($this.limit - $this.cursor) | 0);
			lab1 = true;
		lab1:
			while (lab1 === true) {
				lab1 = false;
				v_5 = (($this.limit - $this.cursor) | 0);
				lab2 = true;
			lab2:
				while (lab2 === true) {
					lab2 = false;
					if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FinnishStemmer.a_5, 7) === 0 ? false : true)) {
						break lab2;
					}
					break lab1;
				}
				$this.cursor = (($this.limit - v_5) | 0);
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 2, "ie")) {
					$this.cursor = (($this.limit - v_3) | 0);
					break lab0;
				}
			}
			cursor$3 = $this.cursor = (($this.limit - v_4) | 0);
			if (cursor$3 <= $this.limit_backward) {
				$this.cursor = (($this.limit - v_3) | 0);
				break lab0;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			$this.bra = $this.cursor;
		}
		break;
	case 8:
		if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, FinnishStemmer.g_V1, 97, 246)) {
			return false;
		}
		if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII($this, FinnishStemmer.g_V1, 97, 246)) {
			return false;
		}
		break;
	case 9:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "e")) {
			return false;
		}
		break;
	}
	if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
		return false;
	}
	$this.B_ending_removed = true;
	return true;
};

FinnishStemmer.r_case_ending$LFinnishStemmer$ = FinnishStemmer$r_case_ending$LFinnishStemmer$;

FinnishStemmer.prototype.r_other_endings$ = function () {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var lab0;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	v_1 = ((this.limit - (cursor$0 = this.cursor)) | 0);
	if (cursor$0 < this.I_p2) {
		return false;
	}
	cursor$1 = this.cursor = this.I_p2;
	v_2 = this.limit_backward;
	this.limit_backward = cursor$1;
	cursor$2 = this.cursor = ((this.limit - v_1) | 0);
	this.ket = cursor$2;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FinnishStemmer.a_7, 14);
	if (among_var === 0) {
		this.limit_backward = v_2;
		return false;
	}
	this.bra = this.cursor;
	this.limit_backward = v_2;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		v_3 = ((this.limit - this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 2, "po")) {
				break lab0;
			}
			return false;
		}
		this.cursor = ((this.limit - v_3) | 0);
		break;
	}
	return (! BaseStemmer$slice_from$LBaseStemmer$S(this, "") ? false : true);
};

FinnishStemmer.prototype.r_other_endings = FinnishStemmer.prototype.r_other_endings$;

function FinnishStemmer$r_other_endings$LFinnishStemmer$($this) {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var lab0;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	v_1 = (($this.limit - (cursor$0 = $this.cursor)) | 0);
	if (cursor$0 < $this.I_p2) {
		return false;
	}
	cursor$1 = $this.cursor = $this.I_p2;
	v_2 = $this.limit_backward;
	$this.limit_backward = cursor$1;
	cursor$2 = $this.cursor = (($this.limit - v_1) | 0);
	$this.ket = cursor$2;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FinnishStemmer.a_7, 14);
	if (among_var === 0) {
		$this.limit_backward = v_2;
		return false;
	}
	$this.bra = $this.cursor;
	$this.limit_backward = v_2;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		v_3 = (($this.limit - $this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 2, "po")) {
				break lab0;
			}
			return false;
		}
		$this.cursor = (($this.limit - v_3) | 0);
		break;
	}
	return (! BaseStemmer$slice_from$LBaseStemmer$S($this, "") ? false : true);
};

FinnishStemmer.r_other_endings$LFinnishStemmer$ = FinnishStemmer$r_other_endings$LFinnishStemmer$;

FinnishStemmer.prototype.r_i_plural$ = function () {
	var v_1;
	var v_2;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	v_1 = ((this.limit - (cursor$0 = this.cursor)) | 0);
	if (cursor$0 < this.I_p1) {
		return false;
	}
	cursor$1 = this.cursor = this.I_p1;
	v_2 = this.limit_backward;
	this.limit_backward = cursor$1;
	cursor$2 = this.cursor = ((this.limit - v_1) | 0);
	this.ket = cursor$2;
	if (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FinnishStemmer.a_8, 2) === 0) {
		this.limit_backward = v_2;
		return false;
	}
	this.bra = this.cursor;
	this.limit_backward = v_2;
	return (! BaseStemmer$slice_from$LBaseStemmer$S(this, "") ? false : true);
};

FinnishStemmer.prototype.r_i_plural = FinnishStemmer.prototype.r_i_plural$;

function FinnishStemmer$r_i_plural$LFinnishStemmer$($this) {
	var v_1;
	var v_2;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	v_1 = (($this.limit - (cursor$0 = $this.cursor)) | 0);
	if (cursor$0 < $this.I_p1) {
		return false;
	}
	cursor$1 = $this.cursor = $this.I_p1;
	v_2 = $this.limit_backward;
	$this.limit_backward = cursor$1;
	cursor$2 = $this.cursor = (($this.limit - v_1) | 0);
	$this.ket = cursor$2;
	if (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FinnishStemmer.a_8, 2) === 0) {
		$this.limit_backward = v_2;
		return false;
	}
	$this.bra = $this.cursor;
	$this.limit_backward = v_2;
	return (! BaseStemmer$slice_from$LBaseStemmer$S($this, "") ? false : true);
};

FinnishStemmer.r_i_plural$LFinnishStemmer$ = FinnishStemmer$r_i_plural$LFinnishStemmer$;

FinnishStemmer.prototype.r_t_plural$ = function () {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var lab0;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var cursor$3;
	var cursor$4;
	var cursor$5;
	var cursor$6;
	v_1 = ((this.limit - (cursor$0 = this.cursor)) | 0);
	if (cursor$0 < this.I_p1) {
		return false;
	}
	cursor$1 = this.cursor = this.I_p1;
	v_2 = this.limit_backward;
	this.limit_backward = cursor$1;
	cursor$2 = this.cursor = ((this.limit - v_1) | 0);
	this.ket = cursor$2;
	if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "t")) {
		this.limit_backward = v_2;
		return false;
	}
	this.bra = cursor$3 = this.cursor;
	v_3 = ((this.limit - cursor$3) | 0);
	if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, FinnishStemmer.g_V1, 97, 246)) {
		this.limit_backward = v_2;
		return false;
	}
	this.cursor = ((this.limit - v_3) | 0);
	if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
		return false;
	}
	this.limit_backward = v_2;
	v_4 = ((this.limit - (cursor$4 = this.cursor)) | 0);
	if (cursor$4 < this.I_p2) {
		return false;
	}
	cursor$5 = this.cursor = this.I_p2;
	v_5 = this.limit_backward;
	this.limit_backward = cursor$5;
	cursor$6 = this.cursor = ((this.limit - v_4) | 0);
	this.ket = cursor$6;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FinnishStemmer.a_9, 2);
	if (among_var === 0) {
		this.limit_backward = v_5;
		return false;
	}
	this.bra = this.cursor;
	this.limit_backward = v_5;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		v_6 = ((this.limit - this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 2, "po")) {
				break lab0;
			}
			return false;
		}
		this.cursor = ((this.limit - v_6) | 0);
		break;
	}
	return (! BaseStemmer$slice_from$LBaseStemmer$S(this, "") ? false : true);
};

FinnishStemmer.prototype.r_t_plural = FinnishStemmer.prototype.r_t_plural$;

function FinnishStemmer$r_t_plural$LFinnishStemmer$($this) {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var lab0;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var cursor$3;
	var cursor$4;
	var cursor$5;
	var cursor$6;
	v_1 = (($this.limit - (cursor$0 = $this.cursor)) | 0);
	if (cursor$0 < $this.I_p1) {
		return false;
	}
	cursor$1 = $this.cursor = $this.I_p1;
	v_2 = $this.limit_backward;
	$this.limit_backward = cursor$1;
	cursor$2 = $this.cursor = (($this.limit - v_1) | 0);
	$this.ket = cursor$2;
	if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "t")) {
		$this.limit_backward = v_2;
		return false;
	}
	$this.bra = cursor$3 = $this.cursor;
	v_3 = (($this.limit - cursor$3) | 0);
	if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, FinnishStemmer.g_V1, 97, 246)) {
		$this.limit_backward = v_2;
		return false;
	}
	$this.cursor = (($this.limit - v_3) | 0);
	if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
		return false;
	}
	$this.limit_backward = v_2;
	v_4 = (($this.limit - (cursor$4 = $this.cursor)) | 0);
	if (cursor$4 < $this.I_p2) {
		return false;
	}
	cursor$5 = $this.cursor = $this.I_p2;
	v_5 = $this.limit_backward;
	$this.limit_backward = cursor$5;
	cursor$6 = $this.cursor = (($this.limit - v_4) | 0);
	$this.ket = cursor$6;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FinnishStemmer.a_9, 2);
	if (among_var === 0) {
		$this.limit_backward = v_5;
		return false;
	}
	$this.bra = $this.cursor;
	$this.limit_backward = v_5;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		v_6 = (($this.limit - $this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 2, "po")) {
				break lab0;
			}
			return false;
		}
		$this.cursor = (($this.limit - v_6) | 0);
		break;
	}
	return (! BaseStemmer$slice_from$LBaseStemmer$S($this, "") ? false : true);
};

FinnishStemmer.r_t_plural$LFinnishStemmer$ = FinnishStemmer$r_t_plural$LFinnishStemmer$;

FinnishStemmer.prototype.r_tidy$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_9;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var lab4;
	var lab5;
	var lab7;
	var s$0;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var limit$0;
	var cursor$3;
	var limit$1;
	var cursor$4;
	var limit$2;
	var cursor$5;
	var limit$3;
	var cursor$6;
	var cursor$7;
	var cursor$8;
	var S_x$0;
	var $__jsx_postinc_t;
	v_1 = ((this.limit - (cursor$0 = this.cursor)) | 0);
	if (cursor$0 < this.I_p1) {
		return false;
	}
	cursor$2 = this.cursor = this.I_p1;
	v_2 = this.limit_backward;
	this.limit_backward = cursor$2;
	cursor$3 = this.cursor = (((limit$0 = this.limit) - v_1) | 0);
	v_3 = ((limit$0 - cursor$3) | 0);
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_4 = ((this.limit - this.cursor) | 0);
		if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FinnishStemmer.a_5, 7) === 0 ? false : true)) {
			break lab0;
		}
		cursor$1 = this.cursor = ((this.limit - v_4) | 0);
		this.ket = cursor$1;
		if (cursor$1 <= this.limit_backward) {
			break lab0;
		}
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		this.bra = this.cursor;
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
	}
	cursor$4 = this.cursor = (((limit$1 = this.limit) - v_3) | 0);
	v_5 = ((limit$1 - cursor$4) | 0);
	lab1 = true;
lab1:
	while (lab1 === true) {
		lab1 = false;
		this.ket = this.cursor;
		if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, FinnishStemmer.g_AEI, 97, 228)) {
			break lab1;
		}
		this.bra = this.cursor;
		if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII(this, FinnishStemmer.g_V1, 97, 246)) {
			break lab1;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
	}
	cursor$5 = this.cursor = (((limit$2 = this.limit) - v_5) | 0);
	v_6 = ((limit$2 - cursor$5) | 0);
	lab2 = true;
lab2:
	while (lab2 === true) {
		lab2 = false;
		this.ket = this.cursor;
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "j")) {
			break lab2;
		}
		this.bra = this.cursor;
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			v_7 = ((this.limit - this.cursor) | 0);
			lab4 = true;
		lab4:
			while (lab4 === true) {
				lab4 = false;
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "o")) {
					break lab4;
				}
				break lab3;
			}
			this.cursor = ((this.limit - v_7) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "u")) {
				break lab2;
			}
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
	}
	cursor$6 = this.cursor = (((limit$3 = this.limit) - v_6) | 0);
	v_8 = ((limit$3 - cursor$6) | 0);
	lab5 = true;
lab5:
	while (lab5 === true) {
		lab5 = false;
		this.ket = this.cursor;
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "o")) {
			break lab5;
		}
		this.bra = this.cursor;
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "j")) {
			break lab5;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
	}
	this.cursor = ((this.limit - v_8) | 0);
	this.limit_backward = v_2;
golab6:
	while (true) {
		v_9 = ((this.limit - this.cursor) | 0);
		lab7 = true;
	lab7:
		while (lab7 === true) {
			lab7 = false;
			if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII(this, FinnishStemmer.g_V1, 97, 246)) {
				break lab7;
			}
			this.cursor = ((this.limit - v_9) | 0);
			break golab6;
		}
		cursor$7 = this.cursor = ((this.limit - v_9) | 0);
		if (cursor$7 <= this.limit_backward) {
			return false;
		}
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	}
	this.ket = cursor$8 = this.cursor;
	if (cursor$8 <= this.limit_backward) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	this.bra = this.cursor;
	S_x$0 = this.S_x = BaseStemmer$slice_to$LBaseStemmer$S(this, this.S_x);
	return (S_x$0 === '' ? false : ! (s$0 = this.S_x, BaseStemmer$eq_s_b$LBaseStemmer$IS(this, s$0.length, s$0)) ? false : ! BaseStemmer$slice_from$LBaseStemmer$S(this, "") ? false : true);
};

FinnishStemmer.prototype.r_tidy = FinnishStemmer.prototype.r_tidy$;

function FinnishStemmer$r_tidy$LFinnishStemmer$($this) {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_9;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var lab4;
	var lab5;
	var lab7;
	var s$0;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var limit$0;
	var cursor$3;
	var limit$1;
	var cursor$4;
	var limit$2;
	var cursor$5;
	var limit$3;
	var cursor$6;
	var cursor$7;
	var cursor$8;
	var S_x$0;
	var $__jsx_postinc_t;
	v_1 = (($this.limit - (cursor$0 = $this.cursor)) | 0);
	if (cursor$0 < $this.I_p1) {
		return false;
	}
	cursor$2 = $this.cursor = $this.I_p1;
	v_2 = $this.limit_backward;
	$this.limit_backward = cursor$2;
	cursor$3 = $this.cursor = (((limit$0 = $this.limit) - v_1) | 0);
	v_3 = ((limit$0 - cursor$3) | 0);
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_4 = (($this.limit - $this.cursor) | 0);
		if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FinnishStemmer.a_5, 7) === 0 ? false : true)) {
			break lab0;
		}
		cursor$1 = $this.cursor = (($this.limit - v_4) | 0);
		$this.ket = cursor$1;
		if (cursor$1 <= $this.limit_backward) {
			break lab0;
		}
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		$this.bra = $this.cursor;
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
	}
	cursor$4 = $this.cursor = (((limit$1 = $this.limit) - v_3) | 0);
	v_5 = ((limit$1 - cursor$4) | 0);
	lab1 = true;
lab1:
	while (lab1 === true) {
		lab1 = false;
		$this.ket = $this.cursor;
		if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, FinnishStemmer.g_AEI, 97, 228)) {
			break lab1;
		}
		$this.bra = $this.cursor;
		if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII($this, FinnishStemmer.g_V1, 97, 246)) {
			break lab1;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
	}
	cursor$5 = $this.cursor = (((limit$2 = $this.limit) - v_5) | 0);
	v_6 = ((limit$2 - cursor$5) | 0);
	lab2 = true;
lab2:
	while (lab2 === true) {
		lab2 = false;
		$this.ket = $this.cursor;
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "j")) {
			break lab2;
		}
		$this.bra = $this.cursor;
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			v_7 = (($this.limit - $this.cursor) | 0);
			lab4 = true;
		lab4:
			while (lab4 === true) {
				lab4 = false;
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "o")) {
					break lab4;
				}
				break lab3;
			}
			$this.cursor = (($this.limit - v_7) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "u")) {
				break lab2;
			}
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
	}
	cursor$6 = $this.cursor = (((limit$3 = $this.limit) - v_6) | 0);
	v_8 = ((limit$3 - cursor$6) | 0);
	lab5 = true;
lab5:
	while (lab5 === true) {
		lab5 = false;
		$this.ket = $this.cursor;
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "o")) {
			break lab5;
		}
		$this.bra = $this.cursor;
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "j")) {
			break lab5;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
	}
	$this.cursor = (($this.limit - v_8) | 0);
	$this.limit_backward = v_2;
golab6:
	while (true) {
		v_9 = (($this.limit - $this.cursor) | 0);
		lab7 = true;
	lab7:
		while (lab7 === true) {
			lab7 = false;
			if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII($this, FinnishStemmer.g_V1, 97, 246)) {
				break lab7;
			}
			$this.cursor = (($this.limit - v_9) | 0);
			break golab6;
		}
		cursor$7 = $this.cursor = (($this.limit - v_9) | 0);
		if (cursor$7 <= $this.limit_backward) {
			return false;
		}
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	}
	$this.ket = cursor$8 = $this.cursor;
	if (cursor$8 <= $this.limit_backward) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	$this.bra = $this.cursor;
	S_x$0 = $this.S_x = BaseStemmer$slice_to$LBaseStemmer$S($this, $this.S_x);
	return (S_x$0 === '' ? false : ! (s$0 = $this.S_x, BaseStemmer$eq_s_b$LBaseStemmer$IS($this, s$0.length, s$0)) ? false : ! BaseStemmer$slice_from$LBaseStemmer$S($this, "") ? false : true);
};

FinnishStemmer.r_tidy$LFinnishStemmer$ = FinnishStemmer$r_tidy$LFinnishStemmer$;

FinnishStemmer.prototype.stem$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var lab4;
	var lab5;
	var lab6;
	var lab7;
	var lab8;
	var lab9;
	var cursor$0;
	var limit$0;
	var cursor$1;
	var limit$1;
	var cursor$2;
	var limit$2;
	var cursor$3;
	var limit$3;
	var cursor$4;
	var limit$4;
	var cursor$5;
	v_1 = this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		if (! FinnishStemmer$r_mark_regions$LFinnishStemmer$(this)) {
			break lab0;
		}
	}
	cursor$0 = this.cursor = v_1;
	this.B_ending_removed = false;
	this.limit_backward = cursor$0;
	cursor$1 = this.cursor = limit$0 = this.limit;
	v_2 = ((limit$0 - cursor$1) | 0);
	lab1 = true;
lab1:
	while (lab1 === true) {
		lab1 = false;
		if (! FinnishStemmer$r_particle_etc$LFinnishStemmer$(this)) {
			break lab1;
		}
	}
	cursor$2 = this.cursor = (((limit$1 = this.limit) - v_2) | 0);
	v_3 = ((limit$1 - cursor$2) | 0);
	lab2 = true;
lab2:
	while (lab2 === true) {
		lab2 = false;
		if (! FinnishStemmer$r_possessive$LFinnishStemmer$(this)) {
			break lab2;
		}
	}
	cursor$3 = this.cursor = (((limit$2 = this.limit) - v_3) | 0);
	v_4 = ((limit$2 - cursor$3) | 0);
	lab3 = true;
lab3:
	while (lab3 === true) {
		lab3 = false;
		if (! FinnishStemmer$r_case_ending$LFinnishStemmer$(this)) {
			break lab3;
		}
	}
	cursor$4 = this.cursor = (((limit$3 = this.limit) - v_4) | 0);
	v_5 = ((limit$3 - cursor$4) | 0);
	lab4 = true;
lab4:
	while (lab4 === true) {
		lab4 = false;
		if (! FinnishStemmer$r_other_endings$LFinnishStemmer$(this)) {
			break lab4;
		}
	}
	this.cursor = ((this.limit - v_5) | 0);
	lab5 = true;
lab5:
	while (lab5 === true) {
		lab5 = false;
		v_6 = ((this.limit - this.cursor) | 0);
		lab6 = true;
	lab6:
		while (lab6 === true) {
			lab6 = false;
			if (! this.B_ending_removed) {
				break lab6;
			}
			v_7 = ((this.limit - this.cursor) | 0);
			lab7 = true;
		lab7:
			while (lab7 === true) {
				lab7 = false;
				if (! FinnishStemmer$r_i_plural$LFinnishStemmer$(this)) {
					break lab7;
				}
			}
			this.cursor = ((this.limit - v_7) | 0);
			break lab5;
		}
		cursor$5 = this.cursor = (((limit$4 = this.limit) - v_6) | 0);
		v_8 = ((limit$4 - cursor$5) | 0);
		lab8 = true;
	lab8:
		while (lab8 === true) {
			lab8 = false;
			if (! FinnishStemmer$r_t_plural$LFinnishStemmer$(this)) {
				break lab8;
			}
		}
		this.cursor = ((this.limit - v_8) | 0);
	}
	lab9 = true;
lab9:
	while (lab9 === true) {
		lab9 = false;
		if (! FinnishStemmer$r_tidy$LFinnishStemmer$(this)) {
			break lab9;
		}
	}
	this.cursor = this.limit_backward;
	return true;
};

FinnishStemmer.prototype.stem = FinnishStemmer.prototype.stem$;

FinnishStemmer.prototype.equals$X = function (o) {
	return o instanceof FinnishStemmer;
};

FinnishStemmer.prototype.equals = FinnishStemmer.prototype.equals$X;

function FinnishStemmer$equals$LFinnishStemmer$X($this, o) {
	return o instanceof FinnishStemmer;
};

FinnishStemmer.equals$LFinnishStemmer$X = FinnishStemmer$equals$LFinnishStemmer$X;

FinnishStemmer.prototype.hashCode$ = function () {
	var classname;
	var hash;
	var i;
	var char;
	classname = "FinnishStemmer";
	hash = 0;
	for (i = 0; i < classname.length; i++) {
		char = classname.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash;
	}
	return (hash | 0);
};

FinnishStemmer.prototype.hashCode = FinnishStemmer.prototype.hashCode$;

function FinnishStemmer$hashCode$LFinnishStemmer$($this) {
	var classname;
	var hash;
	var i;
	var char;
	classname = "FinnishStemmer";
	hash = 0;
	for (i = 0; i < classname.length; i++) {
		char = classname.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash;
	}
	return (hash | 0);
};

FinnishStemmer.hashCode$LFinnishStemmer$ = FinnishStemmer$hashCode$LFinnishStemmer$;

FinnishStemmer.serialVersionUID = 1;
$__jsx_lazy_init(FinnishStemmer, "methodObject", function () {
	return new FinnishStemmer();
});
$__jsx_lazy_init(FinnishStemmer, "a_0", function () {
	return [ new Among("pa", -1, 1), new Among("sti", -1, 2), new Among("kaan", -1, 1), new Among("han", -1, 1), new Among("kin", -1, 1), new Among("h\u00E4n", -1, 1), new Among("k\u00E4\u00E4n", -1, 1), new Among("ko", -1, 1), new Among("p\u00E4", -1, 1), new Among("k\u00F6", -1, 1) ];
});
$__jsx_lazy_init(FinnishStemmer, "a_1", function () {
	return [ new Among("lla", -1, -1), new Among("na", -1, -1), new Among("ssa", -1, -1), new Among("ta", -1, -1), new Among("lta", 3, -1), new Among("sta", 3, -1) ];
});
$__jsx_lazy_init(FinnishStemmer, "a_2", function () {
	return [ new Among("ll\u00E4", -1, -1), new Among("n\u00E4", -1, -1), new Among("ss\u00E4", -1, -1), new Among("t\u00E4", -1, -1), new Among("lt\u00E4", 3, -1), new Among("st\u00E4", 3, -1) ];
});
$__jsx_lazy_init(FinnishStemmer, "a_3", function () {
	return [ new Among("lle", -1, -1), new Among("ine", -1, -1) ];
});
$__jsx_lazy_init(FinnishStemmer, "a_4", function () {
	return [ new Among("nsa", -1, 3), new Among("mme", -1, 3), new Among("nne", -1, 3), new Among("ni", -1, 2), new Among("si", -1, 1), new Among("an", -1, 4), new Among("en", -1, 6), new Among("\u00E4n", -1, 5), new Among("ns\u00E4", -1, 3) ];
});
$__jsx_lazy_init(FinnishStemmer, "a_5", function () {
	return [ new Among("aa", -1, -1), new Among("ee", -1, -1), new Among("ii", -1, -1), new Among("oo", -1, -1), new Among("uu", -1, -1), new Among("\u00E4\u00E4", -1, -1), new Among("\u00F6\u00F6", -1, -1) ];
});
$__jsx_lazy_init(FinnishStemmer, "a_6", function () {
	return [ new Among("a", -1, 8), new Among("lla", 0, -1), new Among("na", 0, -1), new Among("ssa", 0, -1), new Among("ta", 0, -1), new Among("lta", 4, -1), new Among("sta", 4, -1), new Among("tta", 4, 9), new Among("lle", -1, -1), new Among("ine", -1, -1), new Among("ksi", -1, -1), new Among("n", -1, 7), new Among("han", 11, 1), new Among$0("den", 11, -1, (function (instance) {
		var this$0;
		this$0 = instance;
		return (! this$0.eq_s_b$IS(1, "i") ? false : ! this$0.in_grouping_b$AIII(FinnishStemmer.g_V2, 97, 246) ? false : true);
	}), FinnishStemmer.methodObject), new Among$0("seen", 11, -1, (function (instance) {
		var this$0;
		this$0 = instance;
		return (this$0.find_among_b$ALAmong$I(FinnishStemmer.a_5, 7) === 0 ? false : true);
	}), FinnishStemmer.methodObject), new Among("hen", 11, 2), new Among$0("tten", 11, -1, (function (instance) {
		var this$0;
		this$0 = instance;
		return (! this$0.eq_s_b$IS(1, "i") ? false : ! this$0.in_grouping_b$AIII(FinnishStemmer.g_V2, 97, 246) ? false : true);
	}), FinnishStemmer.methodObject), new Among("hin", 11, 3), new Among$0("siin", 11, -1, (function (instance) {
		var this$0;
		this$0 = instance;
		return (! this$0.eq_s_b$IS(1, "i") ? false : ! this$0.in_grouping_b$AIII(FinnishStemmer.g_V2, 97, 246) ? false : true);
	}), FinnishStemmer.methodObject), new Among("hon", 11, 4), new Among("h\u00E4n", 11, 5), new Among("h\u00F6n", 11, 6), new Among("\u00E4", -1, 8), new Among("ll\u00E4", 22, -1), new Among("n\u00E4", 22, -1), new Among("ss\u00E4", 22, -1), new Among("t\u00E4", 22, -1), new Among("lt\u00E4", 26, -1), new Among("st\u00E4", 26, -1), new Among("tt\u00E4", 26, 9) ];
});
$__jsx_lazy_init(FinnishStemmer, "a_7", function () {
	return [ new Among("eja", -1, -1), new Among("mma", -1, 1), new Among("imma", 1, -1), new Among("mpa", -1, 1), new Among("impa", 3, -1), new Among("mmi", -1, 1), new Among("immi", 5, -1), new Among("mpi", -1, 1), new Among("impi", 7, -1), new Among("ej\u00E4", -1, -1), new Among("mm\u00E4", -1, 1), new Among("imm\u00E4", 10, -1), new Among("mp\u00E4", -1, 1), new Among("imp\u00E4", 12, -1) ];
});
$__jsx_lazy_init(FinnishStemmer, "a_8", function () {
	return [ new Among("i", -1, -1), new Among("j", -1, -1) ];
});
$__jsx_lazy_init(FinnishStemmer, "a_9", function () {
	return [ new Among("mma", -1, 1), new Among("imma", 0, -1) ];
});
FinnishStemmer.g_AEI = [ 17, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8 ];
FinnishStemmer.g_V1 = [ 17, 65, 16, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 32 ];
FinnishStemmer.g_V2 = [ 17, 65, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 32 ];
FinnishStemmer.g_particle_end = [ 17, 97, 24, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 32 ];

var $__jsx_classMap = {
	"src/among.jsx": {
		Among: Among,
		Among$SII: Among,
		Among$SIIF$LBaseStemmer$B$LBaseStemmer$: Among$0
	},
	"src/stemmer.jsx": {
		Stemmer: Stemmer,
		Stemmer$: Stemmer
	},
	"src/base-stemmer.jsx": {
		BaseStemmer: BaseStemmer,
		BaseStemmer$: BaseStemmer
	},
	"src/finnish-stemmer.jsx": {
		FinnishStemmer: FinnishStemmer,
		FinnishStemmer$: FinnishStemmer
	}
};


})(JSX);

var Among = JSX.require("src/among.jsx").Among;
var Among$SII = JSX.require("src/among.jsx").Among$SII;
var Stemmer = JSX.require("src/stemmer.jsx").Stemmer;
var BaseStemmer = JSX.require("src/base-stemmer.jsx").BaseStemmer;
var FinnishStemmer = JSX.require("src/finnish-stemmer.jsx").FinnishStemmer;
