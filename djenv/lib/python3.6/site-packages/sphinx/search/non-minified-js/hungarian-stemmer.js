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

function HungarianStemmer() {
	BaseStemmer.call(this);
	this.I_p1 = 0;
};

$__jsx_extend([HungarianStemmer], BaseStemmer);
HungarianStemmer.prototype.copy_from$LHungarianStemmer$ = function (other) {
	this.I_p1 = other.I_p1;
	BaseStemmer$copy_from$LBaseStemmer$LBaseStemmer$(this, other);
};

HungarianStemmer.prototype.copy_from = HungarianStemmer.prototype.copy_from$LHungarianStemmer$;

HungarianStemmer.prototype.r_mark_regions$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var lab0;
	var lab1;
	var lab3;
	var lab4;
	var lab5;
	var lab7;
	var cursor$0;
	var cursor$1;
	var $__jsx_postinc_t;
	this.I_p1 = this.limit;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, HungarianStemmer.g_v, 97, 252)) {
				break lab1;
			}
		golab2:
			while (true) {
				v_2 = this.cursor;
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, HungarianStemmer.g_v, 97, 252)) {
						break lab3;
					}
					this.cursor = v_2;
					break golab2;
				}
				cursor$0 = this.cursor = v_2;
				if (cursor$0 >= this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
			lab4 = true;
		lab4:
			while (lab4 === true) {
				lab4 = false;
				v_3 = this.cursor;
				lab5 = true;
			lab5:
				while (lab5 === true) {
					lab5 = false;
					if (BaseStemmer$find_among$LBaseStemmer$ALAmong$I(this, HungarianStemmer.a_0, 8) === 0) {
						break lab5;
					}
					break lab4;
				}
				cursor$1 = this.cursor = v_3;
				if (cursor$1 >= this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
			this.I_p1 = this.cursor;
			break lab0;
		}
		this.cursor = v_1;
		if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, HungarianStemmer.g_v, 97, 252)) {
			return false;
		}
	golab6:
		while (true) {
			lab7 = true;
		lab7:
			while (lab7 === true) {
				lab7 = false;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, HungarianStemmer.g_v, 97, 252)) {
					break lab7;
				}
				break golab6;
			}
			if (this.cursor >= this.limit) {
				return false;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
		this.I_p1 = this.cursor;
	}
	return true;
};

HungarianStemmer.prototype.r_mark_regions = HungarianStemmer.prototype.r_mark_regions$;

function HungarianStemmer$r_mark_regions$LHungarianStemmer$($this) {
	var v_1;
	var v_2;
	var v_3;
	var lab0;
	var lab1;
	var lab3;
	var lab4;
	var lab5;
	var lab7;
	var cursor$0;
	var cursor$1;
	var $__jsx_postinc_t;
	$this.I_p1 = $this.limit;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = $this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, HungarianStemmer.g_v, 97, 252)) {
				break lab1;
			}
		golab2:
			while (true) {
				v_2 = $this.cursor;
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, HungarianStemmer.g_v, 97, 252)) {
						break lab3;
					}
					$this.cursor = v_2;
					break golab2;
				}
				cursor$0 = $this.cursor = v_2;
				if (cursor$0 >= $this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
			lab4 = true;
		lab4:
			while (lab4 === true) {
				lab4 = false;
				v_3 = $this.cursor;
				lab5 = true;
			lab5:
				while (lab5 === true) {
					lab5 = false;
					if (BaseStemmer$find_among$LBaseStemmer$ALAmong$I($this, HungarianStemmer.a_0, 8) === 0) {
						break lab5;
					}
					break lab4;
				}
				cursor$1 = $this.cursor = v_3;
				if (cursor$1 >= $this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
			$this.I_p1 = $this.cursor;
			break lab0;
		}
		$this.cursor = v_1;
		if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, HungarianStemmer.g_v, 97, 252)) {
			return false;
		}
	golab6:
		while (true) {
			lab7 = true;
		lab7:
			while (lab7 === true) {
				lab7 = false;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, HungarianStemmer.g_v, 97, 252)) {
					break lab7;
				}
				break golab6;
			}
			if ($this.cursor >= $this.limit) {
				return false;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
		$this.I_p1 = $this.cursor;
	}
	return true;
};

HungarianStemmer.r_mark_regions$LHungarianStemmer$ = HungarianStemmer$r_mark_regions$LHungarianStemmer$;

HungarianStemmer.prototype.r_R1$ = function () {
	return (! (this.I_p1 <= this.cursor) ? false : true);
};

HungarianStemmer.prototype.r_R1 = HungarianStemmer.prototype.r_R1$;

function HungarianStemmer$r_R1$LHungarianStemmer$($this) {
	return (! ($this.I_p1 <= $this.cursor) ? false : true);
};

HungarianStemmer.r_R1$LHungarianStemmer$ = HungarianStemmer$r_R1$LHungarianStemmer$;

HungarianStemmer.prototype.r_v_ending$ = function () {
	var among_var;
	var cursor$0;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, HungarianStemmer.a_1, 2);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	if (! (! (this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	}
	return true;
};

HungarianStemmer.prototype.r_v_ending = HungarianStemmer.prototype.r_v_ending$;

function HungarianStemmer$r_v_ending$LHungarianStemmer$($this) {
	var among_var;
	var cursor$0;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, HungarianStemmer.a_1, 2);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	if (! (! ($this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	}
	return true;
};

HungarianStemmer.r_v_ending$LHungarianStemmer$ = HungarianStemmer$r_v_ending$LHungarianStemmer$;

HungarianStemmer.prototype.r_double$ = function () {
	var v_1;
	v_1 = ((this.limit - this.cursor) | 0);
	if (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, HungarianStemmer.a_2, 23) === 0) {
		return false;
	}
	this.cursor = ((this.limit - v_1) | 0);
	return true;
};

HungarianStemmer.prototype.r_double = HungarianStemmer.prototype.r_double$;

function HungarianStemmer$r_double$LHungarianStemmer$($this) {
	var v_1;
	v_1 = (($this.limit - $this.cursor) | 0);
	if (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, HungarianStemmer.a_2, 23) === 0) {
		return false;
	}
	$this.cursor = (($this.limit - v_1) | 0);
	return true;
};

HungarianStemmer.r_double$LHungarianStemmer$ = HungarianStemmer$r_double$LHungarianStemmer$;

HungarianStemmer.prototype.r_undouble$ = function () {
	var c;
	var cursor$0;
	var cursor$1;
	var $__jsx_postinc_t;
	if (this.cursor <= this.limit_backward) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	this.ket = cursor$0 = this.cursor;
	c = (cursor$0 - 1 | 0);
	if (this.limit_backward > c || c > this.limit) {
		return false;
	}
	cursor$1 = this.cursor = c;
	this.bra = cursor$1;
	return (! BaseStemmer$slice_from$LBaseStemmer$S(this, "") ? false : true);
};

HungarianStemmer.prototype.r_undouble = HungarianStemmer.prototype.r_undouble$;

function HungarianStemmer$r_undouble$LHungarianStemmer$($this) {
	var c;
	var cursor$0;
	var cursor$1;
	var $__jsx_postinc_t;
	if ($this.cursor <= $this.limit_backward) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	$this.ket = cursor$0 = $this.cursor;
	c = (cursor$0 - 1 | 0);
	if ($this.limit_backward > c || c > $this.limit) {
		return false;
	}
	cursor$1 = $this.cursor = c;
	$this.bra = cursor$1;
	return (! BaseStemmer$slice_from$LBaseStemmer$S($this, "") ? false : true);
};

HungarianStemmer.r_undouble$LHungarianStemmer$ = HungarianStemmer$r_undouble$LHungarianStemmer$;

HungarianStemmer.prototype.r_instrum$ = function () {
	var among_var;
	var cursor$0;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, HungarianStemmer.a_3, 2);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	if (! (! (this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! HungarianStemmer$r_double$LHungarianStemmer$(this)) {
			return false;
		}
		break;
	case 2:
		if (! HungarianStemmer$r_double$LHungarianStemmer$(this)) {
			return false;
		}
		break;
	}
	return (! BaseStemmer$slice_from$LBaseStemmer$S(this, "") ? false : ! HungarianStemmer$r_undouble$LHungarianStemmer$(this) ? false : true);
};

HungarianStemmer.prototype.r_instrum = HungarianStemmer.prototype.r_instrum$;

function HungarianStemmer$r_instrum$LHungarianStemmer$($this) {
	var among_var;
	var cursor$0;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, HungarianStemmer.a_3, 2);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	if (! (! ($this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! HungarianStemmer$r_double$LHungarianStemmer$($this)) {
			return false;
		}
		break;
	case 2:
		if (! HungarianStemmer$r_double$LHungarianStemmer$($this)) {
			return false;
		}
		break;
	}
	return (! BaseStemmer$slice_from$LBaseStemmer$S($this, "") ? false : ! HungarianStemmer$r_undouble$LHungarianStemmer$($this) ? false : true);
};

HungarianStemmer.r_instrum$LHungarianStemmer$ = HungarianStemmer$r_instrum$LHungarianStemmer$;

HungarianStemmer.prototype.r_case$ = function () {
	var cursor$0;
	this.ket = this.cursor;
	if (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, HungarianStemmer.a_4, 44) === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	return (! (! (this.I_p1 <= cursor$0) ? false : true) ? false : ! BaseStemmer$slice_from$LBaseStemmer$S(this, "") ? false : ! HungarianStemmer$r_v_ending$LHungarianStemmer$(this) ? false : true);
};

HungarianStemmer.prototype.r_case = HungarianStemmer.prototype.r_case$;

function HungarianStemmer$r_case$LHungarianStemmer$($this) {
	var cursor$0;
	$this.ket = $this.cursor;
	if (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, HungarianStemmer.a_4, 44) === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	return (! (! ($this.I_p1 <= cursor$0) ? false : true) ? false : ! BaseStemmer$slice_from$LBaseStemmer$S($this, "") ? false : ! HungarianStemmer$r_v_ending$LHungarianStemmer$($this) ? false : true);
};

HungarianStemmer.r_case$LHungarianStemmer$ = HungarianStemmer$r_case$LHungarianStemmer$;

HungarianStemmer.prototype.r_case_special$ = function () {
	var among_var;
	var cursor$0;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, HungarianStemmer.a_5, 3);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	if (! (! (this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	}
	return true;
};

HungarianStemmer.prototype.r_case_special = HungarianStemmer.prototype.r_case_special$;

function HungarianStemmer$r_case_special$LHungarianStemmer$($this) {
	var among_var;
	var cursor$0;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, HungarianStemmer.a_5, 3);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	if (! (! ($this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	}
	return true;
};

HungarianStemmer.r_case_special$LHungarianStemmer$ = HungarianStemmer$r_case_special$LHungarianStemmer$;

HungarianStemmer.prototype.r_case_other$ = function () {
	var among_var;
	var cursor$0;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, HungarianStemmer.a_6, 6);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	if (! (! (this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	}
	return true;
};

HungarianStemmer.prototype.r_case_other = HungarianStemmer.prototype.r_case_other$;

function HungarianStemmer$r_case_other$LHungarianStemmer$($this) {
	var among_var;
	var cursor$0;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, HungarianStemmer.a_6, 6);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	if (! (! ($this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	}
	return true;
};

HungarianStemmer.r_case_other$LHungarianStemmer$ = HungarianStemmer$r_case_other$LHungarianStemmer$;

HungarianStemmer.prototype.r_factive$ = function () {
	var among_var;
	var cursor$0;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, HungarianStemmer.a_7, 2);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	if (! (! (this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! HungarianStemmer$r_double$LHungarianStemmer$(this)) {
			return false;
		}
		break;
	case 2:
		if (! HungarianStemmer$r_double$LHungarianStemmer$(this)) {
			return false;
		}
		break;
	}
	return (! BaseStemmer$slice_from$LBaseStemmer$S(this, "") ? false : ! HungarianStemmer$r_undouble$LHungarianStemmer$(this) ? false : true);
};

HungarianStemmer.prototype.r_factive = HungarianStemmer.prototype.r_factive$;

function HungarianStemmer$r_factive$LHungarianStemmer$($this) {
	var among_var;
	var cursor$0;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, HungarianStemmer.a_7, 2);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	if (! (! ($this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! HungarianStemmer$r_double$LHungarianStemmer$($this)) {
			return false;
		}
		break;
	case 2:
		if (! HungarianStemmer$r_double$LHungarianStemmer$($this)) {
			return false;
		}
		break;
	}
	return (! BaseStemmer$slice_from$LBaseStemmer$S($this, "") ? false : ! HungarianStemmer$r_undouble$LHungarianStemmer$($this) ? false : true);
};

HungarianStemmer.r_factive$LHungarianStemmer$ = HungarianStemmer$r_factive$LHungarianStemmer$;

HungarianStemmer.prototype.r_plural$ = function () {
	var among_var;
	var cursor$0;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, HungarianStemmer.a_8, 7);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	if (! (! (this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 5:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 7:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	}
	return true;
};

HungarianStemmer.prototype.r_plural = HungarianStemmer.prototype.r_plural$;

function HungarianStemmer$r_plural$LHungarianStemmer$($this) {
	var among_var;
	var cursor$0;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, HungarianStemmer.a_8, 7);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	if (! (! ($this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 5:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 7:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	}
	return true;
};

HungarianStemmer.r_plural$LHungarianStemmer$ = HungarianStemmer$r_plural$LHungarianStemmer$;

HungarianStemmer.prototype.r_owned$ = function () {
	var among_var;
	var cursor$0;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, HungarianStemmer.a_9, 12);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	if (! (! (this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 5:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 7:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 8:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 9:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	}
	return true;
};

HungarianStemmer.prototype.r_owned = HungarianStemmer.prototype.r_owned$;

function HungarianStemmer$r_owned$LHungarianStemmer$($this) {
	var among_var;
	var cursor$0;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, HungarianStemmer.a_9, 12);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	if (! (! ($this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 5:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 7:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 8:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 9:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	}
	return true;
};

HungarianStemmer.r_owned$LHungarianStemmer$ = HungarianStemmer$r_owned$LHungarianStemmer$;

HungarianStemmer.prototype.r_sing_owner$ = function () {
	var among_var;
	var cursor$0;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, HungarianStemmer.a_10, 31);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	if (! (! (this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 5:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 7:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 8:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 9:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 10:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 11:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 12:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 13:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 14:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 15:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 16:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 17:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 18:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 19:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 20:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	}
	return true;
};

HungarianStemmer.prototype.r_sing_owner = HungarianStemmer.prototype.r_sing_owner$;

function HungarianStemmer$r_sing_owner$LHungarianStemmer$($this) {
	var among_var;
	var cursor$0;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, HungarianStemmer.a_10, 31);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	if (! (! ($this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 5:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 7:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 8:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 9:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 10:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 11:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 12:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 13:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 14:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 15:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 16:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 17:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 18:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 19:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 20:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	}
	return true;
};

HungarianStemmer.r_sing_owner$LHungarianStemmer$ = HungarianStemmer$r_sing_owner$LHungarianStemmer$;

HungarianStemmer.prototype.r_plur_owner$ = function () {
	var among_var;
	var cursor$0;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, HungarianStemmer.a_11, 42);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	if (! (! (this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 5:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 7:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 8:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 9:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 10:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 11:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 12:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 13:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 14:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 15:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 16:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 17:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 18:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 19:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 20:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 21:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 22:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 23:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 24:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 25:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 26:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 27:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 28:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 29:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	}
	return true;
};

HungarianStemmer.prototype.r_plur_owner = HungarianStemmer.prototype.r_plur_owner$;

function HungarianStemmer$r_plur_owner$LHungarianStemmer$($this) {
	var among_var;
	var cursor$0;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, HungarianStemmer.a_11, 42);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	if (! (! ($this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 5:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 7:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 8:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 9:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 10:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 11:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 12:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 13:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 14:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 15:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 16:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 17:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 18:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 19:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 20:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 21:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 22:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 23:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 24:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 25:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 26:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 27:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 28:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 29:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	}
	return true;
};

HungarianStemmer.r_plur_owner$LHungarianStemmer$ = HungarianStemmer$r_plur_owner$LHungarianStemmer$;

HungarianStemmer.prototype.stem$ = function () {
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
	var limit$5;
	var cursor$6;
	var limit$6;
	var cursor$7;
	var limit$7;
	var cursor$8;
	v_1 = this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		if (! HungarianStemmer$r_mark_regions$LHungarianStemmer$(this)) {
			break lab0;
		}
	}
	cursor$0 = this.cursor = v_1;
	this.limit_backward = cursor$0;
	cursor$1 = this.cursor = limit$0 = this.limit;
	v_2 = ((limit$0 - cursor$1) | 0);
	lab1 = true;
lab1:
	while (lab1 === true) {
		lab1 = false;
		if (! HungarianStemmer$r_instrum$LHungarianStemmer$(this)) {
			break lab1;
		}
	}
	cursor$2 = this.cursor = (((limit$1 = this.limit) - v_2) | 0);
	v_3 = ((limit$1 - cursor$2) | 0);
	lab2 = true;
lab2:
	while (lab2 === true) {
		lab2 = false;
		if (! HungarianStemmer$r_case$LHungarianStemmer$(this)) {
			break lab2;
		}
	}
	cursor$3 = this.cursor = (((limit$2 = this.limit) - v_3) | 0);
	v_4 = ((limit$2 - cursor$3) | 0);
	lab3 = true;
lab3:
	while (lab3 === true) {
		lab3 = false;
		if (! HungarianStemmer$r_case_special$LHungarianStemmer$(this)) {
			break lab3;
		}
	}
	cursor$4 = this.cursor = (((limit$3 = this.limit) - v_4) | 0);
	v_5 = ((limit$3 - cursor$4) | 0);
	lab4 = true;
lab4:
	while (lab4 === true) {
		lab4 = false;
		if (! HungarianStemmer$r_case_other$LHungarianStemmer$(this)) {
			break lab4;
		}
	}
	cursor$5 = this.cursor = (((limit$4 = this.limit) - v_5) | 0);
	v_6 = ((limit$4 - cursor$5) | 0);
	lab5 = true;
lab5:
	while (lab5 === true) {
		lab5 = false;
		if (! HungarianStemmer$r_factive$LHungarianStemmer$(this)) {
			break lab5;
		}
	}
	cursor$6 = this.cursor = (((limit$5 = this.limit) - v_6) | 0);
	v_7 = ((limit$5 - cursor$6) | 0);
	lab6 = true;
lab6:
	while (lab6 === true) {
		lab6 = false;
		if (! HungarianStemmer$r_owned$LHungarianStemmer$(this)) {
			break lab6;
		}
	}
	cursor$7 = this.cursor = (((limit$6 = this.limit) - v_7) | 0);
	v_8 = ((limit$6 - cursor$7) | 0);
	lab7 = true;
lab7:
	while (lab7 === true) {
		lab7 = false;
		if (! HungarianStemmer$r_sing_owner$LHungarianStemmer$(this)) {
			break lab7;
		}
	}
	cursor$8 = this.cursor = (((limit$7 = this.limit) - v_8) | 0);
	v_9 = ((limit$7 - cursor$8) | 0);
	lab8 = true;
lab8:
	while (lab8 === true) {
		lab8 = false;
		if (! HungarianStemmer$r_plur_owner$LHungarianStemmer$(this)) {
			break lab8;
		}
	}
	this.cursor = ((this.limit - v_9) | 0);
	lab9 = true;
lab9:
	while (lab9 === true) {
		lab9 = false;
		if (! HungarianStemmer$r_plural$LHungarianStemmer$(this)) {
			break lab9;
		}
	}
	this.cursor = this.limit_backward;
	return true;
};

HungarianStemmer.prototype.stem = HungarianStemmer.prototype.stem$;

HungarianStemmer.prototype.equals$X = function (o) {
	return o instanceof HungarianStemmer;
};

HungarianStemmer.prototype.equals = HungarianStemmer.prototype.equals$X;

function HungarianStemmer$equals$LHungarianStemmer$X($this, o) {
	return o instanceof HungarianStemmer;
};

HungarianStemmer.equals$LHungarianStemmer$X = HungarianStemmer$equals$LHungarianStemmer$X;

HungarianStemmer.prototype.hashCode$ = function () {
	var classname;
	var hash;
	var i;
	var char;
	classname = "HungarianStemmer";
	hash = 0;
	for (i = 0; i < classname.length; i++) {
		char = classname.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash;
	}
	return (hash | 0);
};

HungarianStemmer.prototype.hashCode = HungarianStemmer.prototype.hashCode$;

function HungarianStemmer$hashCode$LHungarianStemmer$($this) {
	var classname;
	var hash;
	var i;
	var char;
	classname = "HungarianStemmer";
	hash = 0;
	for (i = 0; i < classname.length; i++) {
		char = classname.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash;
	}
	return (hash | 0);
};

HungarianStemmer.hashCode$LHungarianStemmer$ = HungarianStemmer$hashCode$LHungarianStemmer$;

HungarianStemmer.serialVersionUID = 1;
$__jsx_lazy_init(HungarianStemmer, "methodObject", function () {
	return new HungarianStemmer();
});
$__jsx_lazy_init(HungarianStemmer, "a_0", function () {
	return [ new Among("cs", -1, -1), new Among("dzs", -1, -1), new Among("gy", -1, -1), new Among("ly", -1, -1), new Among("ny", -1, -1), new Among("sz", -1, -1), new Among("ty", -1, -1), new Among("zs", -1, -1) ];
});
$__jsx_lazy_init(HungarianStemmer, "a_1", function () {
	return [ new Among("\u00E1", -1, 1), new Among("\u00E9", -1, 2) ];
});
$__jsx_lazy_init(HungarianStemmer, "a_2", function () {
	return [ new Among("bb", -1, -1), new Among("cc", -1, -1), new Among("dd", -1, -1), new Among("ff", -1, -1), new Among("gg", -1, -1), new Among("jj", -1, -1), new Among("kk", -1, -1), new Among("ll", -1, -1), new Among("mm", -1, -1), new Among("nn", -1, -1), new Among("pp", -1, -1), new Among("rr", -1, -1), new Among("ccs", -1, -1), new Among("ss", -1, -1), new Among("zzs", -1, -1), new Among("tt", -1, -1), new Among("vv", -1, -1), new Among("ggy", -1, -1), new Among("lly", -1, -1), new Among("nny", -1, -1), new Among("tty", -1, -1), new Among("ssz", -1, -1), new Among("zz", -1, -1) ];
});
$__jsx_lazy_init(HungarianStemmer, "a_3", function () {
	return [ new Among("al", -1, 1), new Among("el", -1, 2) ];
});
$__jsx_lazy_init(HungarianStemmer, "a_4", function () {
	return [ new Among("ba", -1, -1), new Among("ra", -1, -1), new Among("be", -1, -1), new Among("re", -1, -1), new Among("ig", -1, -1), new Among("nak", -1, -1), new Among("nek", -1, -1), new Among("val", -1, -1), new Among("vel", -1, -1), new Among("ul", -1, -1), new Among("n\u00E1l", -1, -1), new Among("n\u00E9l", -1, -1), new Among("b\u00F3l", -1, -1), new Among("r\u00F3l", -1, -1), new Among("t\u00F3l", -1, -1), new Among("b\u00F5l", -1, -1), new Among("r\u00F5l", -1, -1), new Among("t\u00F5l", -1, -1), new Among("\u00FCl", -1, -1), new Among("n", -1, -1), new Among("an", 19, -1), new Among("ban", 20, -1), new Among("en", 19, -1), new Among("ben", 22, -1), new Among("k\u00E9ppen", 22, -1), new Among("on", 19, -1), new Among("\u00F6n", 19, -1), new Among("k\u00E9pp", -1, -1), new Among("kor", -1, -1), new Among("t", -1, -1), new Among("at", 29, -1), new Among("et", 29, -1), new Among("k\u00E9nt", 29, -1), new Among("ank\u00E9nt", 32, -1), new Among("enk\u00E9nt", 32, -1), new Among("onk\u00E9nt", 32, -1), new Among("ot", 29, -1), new Among("\u00E9rt", 29, -1), new Among("\u00F6t", 29, -1), new Among("hez", -1, -1), new Among("hoz", -1, -1), new Among("h\u00F6z", -1, -1), new Among("v\u00E1", -1, -1), new Among("v\u00E9", -1, -1) ];
});
$__jsx_lazy_init(HungarianStemmer, "a_5", function () {
	return [ new Among("\u00E1n", -1, 2), new Among("\u00E9n", -1, 1), new Among("\u00E1nk\u00E9nt", -1, 3) ];
});
$__jsx_lazy_init(HungarianStemmer, "a_6", function () {
	return [ new Among("stul", -1, 2), new Among("astul", 0, 1), new Among("\u00E1stul", 0, 3), new Among("st\u00FCl", -1, 2), new Among("est\u00FCl", 3, 1), new Among("\u00E9st\u00FCl", 3, 4) ];
});
$__jsx_lazy_init(HungarianStemmer, "a_7", function () {
	return [ new Among("\u00E1", -1, 1), new Among("\u00E9", -1, 2) ];
});
$__jsx_lazy_init(HungarianStemmer, "a_8", function () {
	return [ new Among("k", -1, 7), new Among("ak", 0, 4), new Among("ek", 0, 6), new Among("ok", 0, 5), new Among("\u00E1k", 0, 1), new Among("\u00E9k", 0, 2), new Among("\u00F6k", 0, 3) ];
});
$__jsx_lazy_init(HungarianStemmer, "a_9", function () {
	return [ new Among("\u00E9i", -1, 7), new Among("\u00E1\u00E9i", 0, 6), new Among("\u00E9\u00E9i", 0, 5), new Among("\u00E9", -1, 9), new Among("k\u00E9", 3, 4), new Among("ak\u00E9", 4, 1), new Among("ek\u00E9", 4, 1), new Among("ok\u00E9", 4, 1), new Among("\u00E1k\u00E9", 4, 3), new Among("\u00E9k\u00E9", 4, 2), new Among("\u00F6k\u00E9", 4, 1), new Among("\u00E9\u00E9", 3, 8) ];
});
$__jsx_lazy_init(HungarianStemmer, "a_10", function () {
	return [ new Among("a", -1, 18), new Among("ja", 0, 17), new Among("d", -1, 16), new Among("ad", 2, 13), new Among("ed", 2, 13), new Among("od", 2, 13), new Among("\u00E1d", 2, 14), new Among("\u00E9d", 2, 15), new Among("\u00F6d", 2, 13), new Among("e", -1, 18), new Among("je", 9, 17), new Among("nk", -1, 4), new Among("unk", 11, 1), new Among("\u00E1nk", 11, 2), new Among("\u00E9nk", 11, 3), new Among("\u00FCnk", 11, 1), new Among("uk", -1, 8), new Among("juk", 16, 7), new Among("\u00E1juk", 17, 5), new Among("\u00FCk", -1, 8), new Among("j\u00FCk", 19, 7), new Among("\u00E9j\u00FCk", 20, 6), new Among("m", -1, 12), new Among("am", 22, 9), new Among("em", 22, 9), new Among("om", 22, 9), new Among("\u00E1m", 22, 10), new Among("\u00E9m", 22, 11), new Among("o", -1, 18), new Among("\u00E1", -1, 19), new Among("\u00E9", -1, 20) ];
});
$__jsx_lazy_init(HungarianStemmer, "a_11", function () {
	return [ new Among("id", -1, 10), new Among("aid", 0, 9), new Among("jaid", 1, 6), new Among("eid", 0, 9), new Among("jeid", 3, 6), new Among("\u00E1id", 0, 7), new Among("\u00E9id", 0, 8), new Among("i", -1, 15), new Among("ai", 7, 14), new Among("jai", 8, 11), new Among("ei", 7, 14), new Among("jei", 10, 11), new Among("\u00E1i", 7, 12), new Among("\u00E9i", 7, 13), new Among("itek", -1, 24), new Among("eitek", 14, 21), new Among("jeitek", 15, 20), new Among("\u00E9itek", 14, 23), new Among("ik", -1, 29), new Among("aik", 18, 26), new Among("jaik", 19, 25), new Among("eik", 18, 26), new Among("jeik", 21, 25), new Among("\u00E1ik", 18, 27), new Among("\u00E9ik", 18, 28), new Among("ink", -1, 20), new Among("aink", 25, 17), new Among("jaink", 26, 16), new Among("eink", 25, 17), new Among("jeink", 28, 16), new Among("\u00E1ink", 25, 18), new Among("\u00E9ink", 25, 19), new Among("aitok", -1, 21), new Among("jaitok", 32, 20), new Among("\u00E1itok", -1, 22), new Among("im", -1, 5), new Among("aim", 35, 4), new Among("jaim", 36, 1), new Among("eim", 35, 4), new Among("jeim", 38, 1), new Among("\u00E1im", 35, 2), new Among("\u00E9im", 35, 3) ];
});
HungarianStemmer.g_v = [ 17, 65, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 17, 52, 14 ];

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
	"src/hungarian-stemmer.jsx": {
		HungarianStemmer: HungarianStemmer,
		HungarianStemmer$: HungarianStemmer
	}
};


})(JSX);

var Among = JSX.require("src/among.jsx").Among;
var Among$SII = JSX.require("src/among.jsx").Among$SII;
var Stemmer = JSX.require("src/stemmer.jsx").Stemmer;
var BaseStemmer = JSX.require("src/base-stemmer.jsx").BaseStemmer;
var HungarianStemmer = JSX.require("src/hungarian-stemmer.jsx").HungarianStemmer;
