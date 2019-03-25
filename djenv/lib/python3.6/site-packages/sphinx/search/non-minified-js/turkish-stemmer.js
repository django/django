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

function TurkishStemmer() {
	BaseStemmer.call(this);
	this.B_continue_stemming_noun_suffixes = false;
	this.I_strlen = 0;
};

$__jsx_extend([TurkishStemmer], BaseStemmer);
TurkishStemmer.prototype.copy_from$LTurkishStemmer$ = function (other) {
	this.B_continue_stemming_noun_suffixes = other.B_continue_stemming_noun_suffixes;
	this.I_strlen = other.I_strlen;
	BaseStemmer$copy_from$LBaseStemmer$LBaseStemmer$(this, other);
};

TurkishStemmer.prototype.copy_from = TurkishStemmer.prototype.copy_from$LTurkishStemmer$;

TurkishStemmer.prototype.r_check_vowel_harmony$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_9;
	var v_10;
	var v_11;
	var lab1;
	var lab2;
	var lab3;
	var lab5;
	var lab6;
	var lab8;
	var lab9;
	var lab11;
	var lab12;
	var lab14;
	var lab15;
	var lab17;
	var lab18;
	var lab20;
	var lab21;
	var lab23;
	var lab25;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var cursor$3;
	var cursor$4;
	var cursor$5;
	var cursor$6;
	var cursor$7;
	var cursor$8;
	var $__jsx_postinc_t;
	v_1 = ((this.limit - this.cursor) | 0);
golab0:
	while (true) {
		v_2 = ((this.limit - this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel, 97, 305)) {
				break lab1;
			}
			this.cursor = ((this.limit - v_2) | 0);
			break golab0;
		}
		cursor$0 = this.cursor = ((this.limit - v_2) | 0);
		if (cursor$0 <= this.limit_backward) {
			return false;
		}
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	}
	lab2 = true;
lab2:
	while (lab2 === true) {
		lab2 = false;
		v_3 = ((this.limit - this.cursor) | 0);
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "a")) {
				break lab3;
			}
		golab4:
			while (true) {
				v_4 = ((this.limit - this.cursor) | 0);
				lab5 = true;
			lab5:
				while (lab5 === true) {
					lab5 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel1, 97, 305)) {
						break lab5;
					}
					this.cursor = ((this.limit - v_4) | 0);
					break golab4;
				}
				cursor$1 = this.cursor = ((this.limit - v_4) | 0);
				if (cursor$1 <= this.limit_backward) {
					break lab3;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			break lab2;
		}
		this.cursor = ((this.limit - v_3) | 0);
		lab6 = true;
	lab6:
		while (lab6 === true) {
			lab6 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "e")) {
				break lab6;
			}
		golab7:
			while (true) {
				v_5 = ((this.limit - this.cursor) | 0);
				lab8 = true;
			lab8:
				while (lab8 === true) {
					lab8 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel2, 101, 252)) {
						break lab8;
					}
					this.cursor = ((this.limit - v_5) | 0);
					break golab7;
				}
				cursor$2 = this.cursor = ((this.limit - v_5) | 0);
				if (cursor$2 <= this.limit_backward) {
					break lab6;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			break lab2;
		}
		this.cursor = ((this.limit - v_3) | 0);
		lab9 = true;
	lab9:
		while (lab9 === true) {
			lab9 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "\u0131")) {
				break lab9;
			}
		golab10:
			while (true) {
				v_6 = ((this.limit - this.cursor) | 0);
				lab11 = true;
			lab11:
				while (lab11 === true) {
					lab11 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel3, 97, 305)) {
						break lab11;
					}
					this.cursor = ((this.limit - v_6) | 0);
					break golab10;
				}
				cursor$3 = this.cursor = ((this.limit - v_6) | 0);
				if (cursor$3 <= this.limit_backward) {
					break lab9;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			break lab2;
		}
		this.cursor = ((this.limit - v_3) | 0);
		lab12 = true;
	lab12:
		while (lab12 === true) {
			lab12 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "i")) {
				break lab12;
			}
		golab13:
			while (true) {
				v_7 = ((this.limit - this.cursor) | 0);
				lab14 = true;
			lab14:
				while (lab14 === true) {
					lab14 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel4, 101, 105)) {
						break lab14;
					}
					this.cursor = ((this.limit - v_7) | 0);
					break golab13;
				}
				cursor$4 = this.cursor = ((this.limit - v_7) | 0);
				if (cursor$4 <= this.limit_backward) {
					break lab12;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			break lab2;
		}
		this.cursor = ((this.limit - v_3) | 0);
		lab15 = true;
	lab15:
		while (lab15 === true) {
			lab15 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "o")) {
				break lab15;
			}
		golab16:
			while (true) {
				v_8 = ((this.limit - this.cursor) | 0);
				lab17 = true;
			lab17:
				while (lab17 === true) {
					lab17 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel5, 111, 117)) {
						break lab17;
					}
					this.cursor = ((this.limit - v_8) | 0);
					break golab16;
				}
				cursor$5 = this.cursor = ((this.limit - v_8) | 0);
				if (cursor$5 <= this.limit_backward) {
					break lab15;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			break lab2;
		}
		this.cursor = ((this.limit - v_3) | 0);
		lab18 = true;
	lab18:
		while (lab18 === true) {
			lab18 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "\u00F6")) {
				break lab18;
			}
		golab19:
			while (true) {
				v_9 = ((this.limit - this.cursor) | 0);
				lab20 = true;
			lab20:
				while (lab20 === true) {
					lab20 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel6, 246, 252)) {
						break lab20;
					}
					this.cursor = ((this.limit - v_9) | 0);
					break golab19;
				}
				cursor$6 = this.cursor = ((this.limit - v_9) | 0);
				if (cursor$6 <= this.limit_backward) {
					break lab18;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			break lab2;
		}
		this.cursor = ((this.limit - v_3) | 0);
		lab21 = true;
	lab21:
		while (lab21 === true) {
			lab21 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "u")) {
				break lab21;
			}
		golab22:
			while (true) {
				v_10 = ((this.limit - this.cursor) | 0);
				lab23 = true;
			lab23:
				while (lab23 === true) {
					lab23 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel5, 111, 117)) {
						break lab23;
					}
					this.cursor = ((this.limit - v_10) | 0);
					break golab22;
				}
				cursor$7 = this.cursor = ((this.limit - v_10) | 0);
				if (cursor$7 <= this.limit_backward) {
					break lab21;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			break lab2;
		}
		this.cursor = ((this.limit - v_3) | 0);
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "\u00FC")) {
			return false;
		}
	golab24:
		while (true) {
			v_11 = ((this.limit - this.cursor) | 0);
			lab25 = true;
		lab25:
			while (lab25 === true) {
				lab25 = false;
				if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel6, 246, 252)) {
					break lab25;
				}
				this.cursor = ((this.limit - v_11) | 0);
				break golab24;
			}
			cursor$8 = this.cursor = ((this.limit - v_11) | 0);
			if (cursor$8 <= this.limit_backward) {
				return false;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		}
	}
	this.cursor = ((this.limit - v_1) | 0);
	return true;
};

TurkishStemmer.prototype.r_check_vowel_harmony = TurkishStemmer.prototype.r_check_vowel_harmony$;

function TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_9;
	var v_10;
	var v_11;
	var lab1;
	var lab2;
	var lab3;
	var lab5;
	var lab6;
	var lab8;
	var lab9;
	var lab11;
	var lab12;
	var lab14;
	var lab15;
	var lab17;
	var lab18;
	var lab20;
	var lab21;
	var lab23;
	var lab25;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var cursor$3;
	var cursor$4;
	var cursor$5;
	var cursor$6;
	var cursor$7;
	var cursor$8;
	var $__jsx_postinc_t;
	v_1 = (($this.limit - $this.cursor) | 0);
golab0:
	while (true) {
		v_2 = (($this.limit - $this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel, 97, 305)) {
				break lab1;
			}
			$this.cursor = (($this.limit - v_2) | 0);
			break golab0;
		}
		cursor$0 = $this.cursor = (($this.limit - v_2) | 0);
		if (cursor$0 <= $this.limit_backward) {
			return false;
		}
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	}
	lab2 = true;
lab2:
	while (lab2 === true) {
		lab2 = false;
		v_3 = (($this.limit - $this.cursor) | 0);
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "a")) {
				break lab3;
			}
		golab4:
			while (true) {
				v_4 = (($this.limit - $this.cursor) | 0);
				lab5 = true;
			lab5:
				while (lab5 === true) {
					lab5 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel1, 97, 305)) {
						break lab5;
					}
					$this.cursor = (($this.limit - v_4) | 0);
					break golab4;
				}
				cursor$1 = $this.cursor = (($this.limit - v_4) | 0);
				if (cursor$1 <= $this.limit_backward) {
					break lab3;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			break lab2;
		}
		$this.cursor = (($this.limit - v_3) | 0);
		lab6 = true;
	lab6:
		while (lab6 === true) {
			lab6 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "e")) {
				break lab6;
			}
		golab7:
			while (true) {
				v_5 = (($this.limit - $this.cursor) | 0);
				lab8 = true;
			lab8:
				while (lab8 === true) {
					lab8 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel2, 101, 252)) {
						break lab8;
					}
					$this.cursor = (($this.limit - v_5) | 0);
					break golab7;
				}
				cursor$2 = $this.cursor = (($this.limit - v_5) | 0);
				if (cursor$2 <= $this.limit_backward) {
					break lab6;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			break lab2;
		}
		$this.cursor = (($this.limit - v_3) | 0);
		lab9 = true;
	lab9:
		while (lab9 === true) {
			lab9 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "\u0131")) {
				break lab9;
			}
		golab10:
			while (true) {
				v_6 = (($this.limit - $this.cursor) | 0);
				lab11 = true;
			lab11:
				while (lab11 === true) {
					lab11 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel3, 97, 305)) {
						break lab11;
					}
					$this.cursor = (($this.limit - v_6) | 0);
					break golab10;
				}
				cursor$3 = $this.cursor = (($this.limit - v_6) | 0);
				if (cursor$3 <= $this.limit_backward) {
					break lab9;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			break lab2;
		}
		$this.cursor = (($this.limit - v_3) | 0);
		lab12 = true;
	lab12:
		while (lab12 === true) {
			lab12 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "i")) {
				break lab12;
			}
		golab13:
			while (true) {
				v_7 = (($this.limit - $this.cursor) | 0);
				lab14 = true;
			lab14:
				while (lab14 === true) {
					lab14 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel4, 101, 105)) {
						break lab14;
					}
					$this.cursor = (($this.limit - v_7) | 0);
					break golab13;
				}
				cursor$4 = $this.cursor = (($this.limit - v_7) | 0);
				if (cursor$4 <= $this.limit_backward) {
					break lab12;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			break lab2;
		}
		$this.cursor = (($this.limit - v_3) | 0);
		lab15 = true;
	lab15:
		while (lab15 === true) {
			lab15 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "o")) {
				break lab15;
			}
		golab16:
			while (true) {
				v_8 = (($this.limit - $this.cursor) | 0);
				lab17 = true;
			lab17:
				while (lab17 === true) {
					lab17 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel5, 111, 117)) {
						break lab17;
					}
					$this.cursor = (($this.limit - v_8) | 0);
					break golab16;
				}
				cursor$5 = $this.cursor = (($this.limit - v_8) | 0);
				if (cursor$5 <= $this.limit_backward) {
					break lab15;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			break lab2;
		}
		$this.cursor = (($this.limit - v_3) | 0);
		lab18 = true;
	lab18:
		while (lab18 === true) {
			lab18 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "\u00F6")) {
				break lab18;
			}
		golab19:
			while (true) {
				v_9 = (($this.limit - $this.cursor) | 0);
				lab20 = true;
			lab20:
				while (lab20 === true) {
					lab20 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel6, 246, 252)) {
						break lab20;
					}
					$this.cursor = (($this.limit - v_9) | 0);
					break golab19;
				}
				cursor$6 = $this.cursor = (($this.limit - v_9) | 0);
				if (cursor$6 <= $this.limit_backward) {
					break lab18;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			break lab2;
		}
		$this.cursor = (($this.limit - v_3) | 0);
		lab21 = true;
	lab21:
		while (lab21 === true) {
			lab21 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "u")) {
				break lab21;
			}
		golab22:
			while (true) {
				v_10 = (($this.limit - $this.cursor) | 0);
				lab23 = true;
			lab23:
				while (lab23 === true) {
					lab23 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel5, 111, 117)) {
						break lab23;
					}
					$this.cursor = (($this.limit - v_10) | 0);
					break golab22;
				}
				cursor$7 = $this.cursor = (($this.limit - v_10) | 0);
				if (cursor$7 <= $this.limit_backward) {
					break lab21;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			break lab2;
		}
		$this.cursor = (($this.limit - v_3) | 0);
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "\u00FC")) {
			return false;
		}
	golab24:
		while (true) {
			v_11 = (($this.limit - $this.cursor) | 0);
			lab25 = true;
		lab25:
			while (lab25 === true) {
				lab25 = false;
				if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel6, 246, 252)) {
					break lab25;
				}
				$this.cursor = (($this.limit - v_11) | 0);
				break golab24;
			}
			cursor$8 = $this.cursor = (($this.limit - v_11) | 0);
			if (cursor$8 <= $this.limit_backward) {
				return false;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		}
	}
	$this.cursor = (($this.limit - v_1) | 0);
	return true;
};

TurkishStemmer.r_check_vowel_harmony$LTurkishStemmer$ = TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_suffix_with_optional_n_consonant$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	var limit$0;
	var cursor$1;
	var limit$1;
	var cursor$2;
	var $__jsx_postinc_t;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = ((this.limit - this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_2 = ((this.limit - this.cursor) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "n")) {
				break lab1;
			}
			cursor$0 = this.cursor = ((this.limit - v_2) | 0);
			if (cursor$0 <= this.limit_backward) {
				break lab1;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			v_3 = ((this.limit - this.cursor) | 0);
			if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel, 97, 305)) {
				break lab1;
			}
			this.cursor = ((this.limit - v_3) | 0);
			break lab0;
		}
		cursor$1 = this.cursor = (((limit$0 = this.limit) - v_1) | 0);
		v_4 = ((limit$0 - cursor$1) | 0);
		lab2 = true;
	lab2:
		while (lab2 === true) {
			lab2 = false;
			v_5 = ((this.limit - this.cursor) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "n")) {
				break lab2;
			}
			this.cursor = ((this.limit - v_5) | 0);
			return false;
		}
		cursor$2 = this.cursor = (((limit$1 = this.limit) - v_4) | 0);
		v_6 = ((limit$1 - cursor$2) | 0);
		if (cursor$2 <= this.limit_backward) {
			return false;
		}
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel, 97, 305)) {
			return false;
		}
		this.cursor = ((this.limit - v_6) | 0);
	}
	return true;
};

TurkishStemmer.prototype.r_mark_suffix_with_optional_n_consonant = TurkishStemmer.prototype.r_mark_suffix_with_optional_n_consonant$;

function TurkishStemmer$r_mark_suffix_with_optional_n_consonant$LTurkishStemmer$($this) {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	var limit$0;
	var cursor$1;
	var limit$1;
	var cursor$2;
	var $__jsx_postinc_t;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = (($this.limit - $this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_2 = (($this.limit - $this.cursor) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "n")) {
				break lab1;
			}
			cursor$0 = $this.cursor = (($this.limit - v_2) | 0);
			if (cursor$0 <= $this.limit_backward) {
				break lab1;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			v_3 = (($this.limit - $this.cursor) | 0);
			if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel, 97, 305)) {
				break lab1;
			}
			$this.cursor = (($this.limit - v_3) | 0);
			break lab0;
		}
		cursor$1 = $this.cursor = (((limit$0 = $this.limit) - v_1) | 0);
		v_4 = ((limit$0 - cursor$1) | 0);
		lab2 = true;
	lab2:
		while (lab2 === true) {
			lab2 = false;
			v_5 = (($this.limit - $this.cursor) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "n")) {
				break lab2;
			}
			$this.cursor = (($this.limit - v_5) | 0);
			return false;
		}
		cursor$2 = $this.cursor = (((limit$1 = $this.limit) - v_4) | 0);
		v_6 = ((limit$1 - cursor$2) | 0);
		if (cursor$2 <= $this.limit_backward) {
			return false;
		}
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel, 97, 305)) {
			return false;
		}
		$this.cursor = (($this.limit - v_6) | 0);
	}
	return true;
};

TurkishStemmer.r_mark_suffix_with_optional_n_consonant$LTurkishStemmer$ = TurkishStemmer$r_mark_suffix_with_optional_n_consonant$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_suffix_with_optional_s_consonant$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	var limit$0;
	var cursor$1;
	var limit$1;
	var cursor$2;
	var $__jsx_postinc_t;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = ((this.limit - this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_2 = ((this.limit - this.cursor) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "s")) {
				break lab1;
			}
			cursor$0 = this.cursor = ((this.limit - v_2) | 0);
			if (cursor$0 <= this.limit_backward) {
				break lab1;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			v_3 = ((this.limit - this.cursor) | 0);
			if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel, 97, 305)) {
				break lab1;
			}
			this.cursor = ((this.limit - v_3) | 0);
			break lab0;
		}
		cursor$1 = this.cursor = (((limit$0 = this.limit) - v_1) | 0);
		v_4 = ((limit$0 - cursor$1) | 0);
		lab2 = true;
	lab2:
		while (lab2 === true) {
			lab2 = false;
			v_5 = ((this.limit - this.cursor) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "s")) {
				break lab2;
			}
			this.cursor = ((this.limit - v_5) | 0);
			return false;
		}
		cursor$2 = this.cursor = (((limit$1 = this.limit) - v_4) | 0);
		v_6 = ((limit$1 - cursor$2) | 0);
		if (cursor$2 <= this.limit_backward) {
			return false;
		}
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel, 97, 305)) {
			return false;
		}
		this.cursor = ((this.limit - v_6) | 0);
	}
	return true;
};

TurkishStemmer.prototype.r_mark_suffix_with_optional_s_consonant = TurkishStemmer.prototype.r_mark_suffix_with_optional_s_consonant$;

function TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$($this) {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	var limit$0;
	var cursor$1;
	var limit$1;
	var cursor$2;
	var $__jsx_postinc_t;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = (($this.limit - $this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_2 = (($this.limit - $this.cursor) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "s")) {
				break lab1;
			}
			cursor$0 = $this.cursor = (($this.limit - v_2) | 0);
			if (cursor$0 <= $this.limit_backward) {
				break lab1;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			v_3 = (($this.limit - $this.cursor) | 0);
			if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel, 97, 305)) {
				break lab1;
			}
			$this.cursor = (($this.limit - v_3) | 0);
			break lab0;
		}
		cursor$1 = $this.cursor = (((limit$0 = $this.limit) - v_1) | 0);
		v_4 = ((limit$0 - cursor$1) | 0);
		lab2 = true;
	lab2:
		while (lab2 === true) {
			lab2 = false;
			v_5 = (($this.limit - $this.cursor) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "s")) {
				break lab2;
			}
			$this.cursor = (($this.limit - v_5) | 0);
			return false;
		}
		cursor$2 = $this.cursor = (((limit$1 = $this.limit) - v_4) | 0);
		v_6 = ((limit$1 - cursor$2) | 0);
		if (cursor$2 <= $this.limit_backward) {
			return false;
		}
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel, 97, 305)) {
			return false;
		}
		$this.cursor = (($this.limit - v_6) | 0);
	}
	return true;
};

TurkishStemmer.r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$ = TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_suffix_with_optional_y_consonant$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	var limit$0;
	var cursor$1;
	var limit$1;
	var cursor$2;
	var $__jsx_postinc_t;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = ((this.limit - this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_2 = ((this.limit - this.cursor) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "y")) {
				break lab1;
			}
			cursor$0 = this.cursor = ((this.limit - v_2) | 0);
			if (cursor$0 <= this.limit_backward) {
				break lab1;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			v_3 = ((this.limit - this.cursor) | 0);
			if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel, 97, 305)) {
				break lab1;
			}
			this.cursor = ((this.limit - v_3) | 0);
			break lab0;
		}
		cursor$1 = this.cursor = (((limit$0 = this.limit) - v_1) | 0);
		v_4 = ((limit$0 - cursor$1) | 0);
		lab2 = true;
	lab2:
		while (lab2 === true) {
			lab2 = false;
			v_5 = ((this.limit - this.cursor) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "y")) {
				break lab2;
			}
			this.cursor = ((this.limit - v_5) | 0);
			return false;
		}
		cursor$2 = this.cursor = (((limit$1 = this.limit) - v_4) | 0);
		v_6 = ((limit$1 - cursor$2) | 0);
		if (cursor$2 <= this.limit_backward) {
			return false;
		}
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel, 97, 305)) {
			return false;
		}
		this.cursor = ((this.limit - v_6) | 0);
	}
	return true;
};

TurkishStemmer.prototype.r_mark_suffix_with_optional_y_consonant = TurkishStemmer.prototype.r_mark_suffix_with_optional_y_consonant$;

function TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	var limit$0;
	var cursor$1;
	var limit$1;
	var cursor$2;
	var $__jsx_postinc_t;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = (($this.limit - $this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_2 = (($this.limit - $this.cursor) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "y")) {
				break lab1;
			}
			cursor$0 = $this.cursor = (($this.limit - v_2) | 0);
			if (cursor$0 <= $this.limit_backward) {
				break lab1;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			v_3 = (($this.limit - $this.cursor) | 0);
			if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel, 97, 305)) {
				break lab1;
			}
			$this.cursor = (($this.limit - v_3) | 0);
			break lab0;
		}
		cursor$1 = $this.cursor = (((limit$0 = $this.limit) - v_1) | 0);
		v_4 = ((limit$0 - cursor$1) | 0);
		lab2 = true;
	lab2:
		while (lab2 === true) {
			lab2 = false;
			v_5 = (($this.limit - $this.cursor) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "y")) {
				break lab2;
			}
			$this.cursor = (($this.limit - v_5) | 0);
			return false;
		}
		cursor$2 = $this.cursor = (((limit$1 = $this.limit) - v_4) | 0);
		v_6 = ((limit$1 - cursor$2) | 0);
		if (cursor$2 <= $this.limit_backward) {
			return false;
		}
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel, 97, 305)) {
			return false;
		}
		$this.cursor = (($this.limit - v_6) | 0);
	}
	return true;
};

TurkishStemmer.r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$ = TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_suffix_with_optional_U_vowel$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	var limit$0;
	var cursor$1;
	var limit$1;
	var cursor$2;
	var $__jsx_postinc_t;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = ((this.limit - this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_2 = ((this.limit - this.cursor) | 0);
			if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_U, 105, 305)) {
				break lab1;
			}
			cursor$0 = this.cursor = ((this.limit - v_2) | 0);
			if (cursor$0 <= this.limit_backward) {
				break lab1;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			v_3 = ((this.limit - this.cursor) | 0);
			if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel, 97, 305)) {
				break lab1;
			}
			this.cursor = ((this.limit - v_3) | 0);
			break lab0;
		}
		cursor$1 = this.cursor = (((limit$0 = this.limit) - v_1) | 0);
		v_4 = ((limit$0 - cursor$1) | 0);
		lab2 = true;
	lab2:
		while (lab2 === true) {
			lab2 = false;
			v_5 = ((this.limit - this.cursor) | 0);
			if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_U, 105, 305)) {
				break lab2;
			}
			this.cursor = ((this.limit - v_5) | 0);
			return false;
		}
		cursor$2 = this.cursor = (((limit$1 = this.limit) - v_4) | 0);
		v_6 = ((limit$1 - cursor$2) | 0);
		if (cursor$2 <= this.limit_backward) {
			return false;
		}
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel, 97, 305)) {
			return false;
		}
		this.cursor = ((this.limit - v_6) | 0);
	}
	return true;
};

TurkishStemmer.prototype.r_mark_suffix_with_optional_U_vowel = TurkishStemmer.prototype.r_mark_suffix_with_optional_U_vowel$;

function TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$($this) {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	var limit$0;
	var cursor$1;
	var limit$1;
	var cursor$2;
	var $__jsx_postinc_t;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = (($this.limit - $this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_2 = (($this.limit - $this.cursor) | 0);
			if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_U, 105, 305)) {
				break lab1;
			}
			cursor$0 = $this.cursor = (($this.limit - v_2) | 0);
			if (cursor$0 <= $this.limit_backward) {
				break lab1;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			v_3 = (($this.limit - $this.cursor) | 0);
			if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel, 97, 305)) {
				break lab1;
			}
			$this.cursor = (($this.limit - v_3) | 0);
			break lab0;
		}
		cursor$1 = $this.cursor = (((limit$0 = $this.limit) - v_1) | 0);
		v_4 = ((limit$0 - cursor$1) | 0);
		lab2 = true;
	lab2:
		while (lab2 === true) {
			lab2 = false;
			v_5 = (($this.limit - $this.cursor) | 0);
			if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_U, 105, 305)) {
				break lab2;
			}
			$this.cursor = (($this.limit - v_5) | 0);
			return false;
		}
		cursor$2 = $this.cursor = (((limit$1 = $this.limit) - v_4) | 0);
		v_6 = ((limit$1 - cursor$2) | 0);
		if (cursor$2 <= $this.limit_backward) {
			return false;
		}
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel, 97, 305)) {
			return false;
		}
		$this.cursor = (($this.limit - v_6) | 0);
	}
	return true;
};

TurkishStemmer.r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$ = TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_possessives$ = function () {
	return (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$(this) ? false : true);
};

TurkishStemmer.prototype.r_mark_possessives = TurkishStemmer.prototype.r_mark_possessives$;

function TurkishStemmer$r_mark_possessives$LTurkishStemmer$($this) {
	return (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$($this) ? false : true);
};

TurkishStemmer.r_mark_possessives$LTurkishStemmer$ = TurkishStemmer$r_mark_possessives$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_sU$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$(this) ? false : true);
};

TurkishStemmer.prototype.r_mark_sU = TurkishStemmer.prototype.r_mark_sU$;

function TurkishStemmer$r_mark_sU$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$($this) ? false : true);
};

TurkishStemmer.r_mark_sU$LTurkishStemmer$ = TurkishStemmer$r_mark_sU$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_lArI$ = function () {
	return (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_1, 2) === 0 ? false : true);
};

TurkishStemmer.prototype.r_mark_lArI = TurkishStemmer.prototype.r_mark_lArI$;

function TurkishStemmer$r_mark_lArI$LTurkishStemmer$($this) {
	return (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_1, 2) === 0 ? false : true);
};

TurkishStemmer.r_mark_lArI$LTurkishStemmer$ = TurkishStemmer$r_mark_lArI$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_yU$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true);
};

TurkishStemmer.prototype.r_mark_yU = TurkishStemmer.prototype.r_mark_yU$;

function TurkishStemmer$r_mark_yU$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true);
};

TurkishStemmer.r_mark_yU$LTurkishStemmer$ = TurkishStemmer$r_mark_yU$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_nU$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_2, 4) === 0 ? false : true);
};

TurkishStemmer.prototype.r_mark_nU = TurkishStemmer.prototype.r_mark_nU$;

function TurkishStemmer$r_mark_nU$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_2, 4) === 0 ? false : true);
};

TurkishStemmer.r_mark_nU$LTurkishStemmer$ = TurkishStemmer$r_mark_nU$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_nUn$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_3, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_n_consonant$LTurkishStemmer$(this) ? false : true);
};

TurkishStemmer.prototype.r_mark_nUn = TurkishStemmer.prototype.r_mark_nUn$;

function TurkishStemmer$r_mark_nUn$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_3, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_n_consonant$LTurkishStemmer$($this) ? false : true);
};

TurkishStemmer.r_mark_nUn$LTurkishStemmer$ = TurkishStemmer$r_mark_nUn$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_yA$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_4, 2) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true);
};

TurkishStemmer.prototype.r_mark_yA = TurkishStemmer.prototype.r_mark_yA$;

function TurkishStemmer$r_mark_yA$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_4, 2) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true);
};

TurkishStemmer.r_mark_yA$LTurkishStemmer$ = TurkishStemmer$r_mark_yA$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_nA$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_5, 2) === 0 ? false : true);
};

TurkishStemmer.prototype.r_mark_nA = TurkishStemmer.prototype.r_mark_nA$;

function TurkishStemmer$r_mark_nA$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_5, 2) === 0 ? false : true);
};

TurkishStemmer.r_mark_nA$LTurkishStemmer$ = TurkishStemmer$r_mark_nA$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_DA$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_6, 4) === 0 ? false : true);
};

TurkishStemmer.prototype.r_mark_DA = TurkishStemmer.prototype.r_mark_DA$;

function TurkishStemmer$r_mark_DA$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_6, 4) === 0 ? false : true);
};

TurkishStemmer.r_mark_DA$LTurkishStemmer$ = TurkishStemmer$r_mark_DA$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_ndA$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_7, 2) === 0 ? false : true);
};

TurkishStemmer.prototype.r_mark_ndA = TurkishStemmer.prototype.r_mark_ndA$;

function TurkishStemmer$r_mark_ndA$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_7, 2) === 0 ? false : true);
};

TurkishStemmer.r_mark_ndA$LTurkishStemmer$ = TurkishStemmer$r_mark_ndA$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_DAn$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_8, 4) === 0 ? false : true);
};

TurkishStemmer.prototype.r_mark_DAn = TurkishStemmer.prototype.r_mark_DAn$;

function TurkishStemmer$r_mark_DAn$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_8, 4) === 0 ? false : true);
};

TurkishStemmer.r_mark_DAn$LTurkishStemmer$ = TurkishStemmer$r_mark_DAn$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_ndAn$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_9, 2) === 0 ? false : true);
};

TurkishStemmer.prototype.r_mark_ndAn = TurkishStemmer.prototype.r_mark_ndAn$;

function TurkishStemmer$r_mark_ndAn$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_9, 2) === 0 ? false : true);
};

TurkishStemmer.r_mark_ndAn$LTurkishStemmer$ = TurkishStemmer$r_mark_ndAn$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_ylA$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_10, 2) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true);
};

TurkishStemmer.prototype.r_mark_ylA = TurkishStemmer.prototype.r_mark_ylA$;

function TurkishStemmer$r_mark_ylA$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_10, 2) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true);
};

TurkishStemmer.r_mark_ylA$LTurkishStemmer$ = TurkishStemmer$r_mark_ylA$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_ki$ = function () {
	return (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 2, "ki") ? false : true);
};

TurkishStemmer.prototype.r_mark_ki = TurkishStemmer.prototype.r_mark_ki$;

function TurkishStemmer$r_mark_ki$LTurkishStemmer$($this) {
	return (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 2, "ki") ? false : true);
};

TurkishStemmer.r_mark_ki$LTurkishStemmer$ = TurkishStemmer$r_mark_ki$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_ncA$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_11, 2) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_n_consonant$LTurkishStemmer$(this) ? false : true);
};

TurkishStemmer.prototype.r_mark_ncA = TurkishStemmer.prototype.r_mark_ncA$;

function TurkishStemmer$r_mark_ncA$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_11, 2) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_n_consonant$LTurkishStemmer$($this) ? false : true);
};

TurkishStemmer.r_mark_ncA$LTurkishStemmer$ = TurkishStemmer$r_mark_ncA$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_yUm$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_12, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true);
};

TurkishStemmer.prototype.r_mark_yUm = TurkishStemmer.prototype.r_mark_yUm$;

function TurkishStemmer$r_mark_yUm$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_12, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true);
};

TurkishStemmer.r_mark_yUm$LTurkishStemmer$ = TurkishStemmer$r_mark_yUm$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_sUn$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_13, 4) === 0 ? false : true);
};

TurkishStemmer.prototype.r_mark_sUn = TurkishStemmer.prototype.r_mark_sUn$;

function TurkishStemmer$r_mark_sUn$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_13, 4) === 0 ? false : true);
};

TurkishStemmer.r_mark_sUn$LTurkishStemmer$ = TurkishStemmer$r_mark_sUn$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_yUz$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_14, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true);
};

TurkishStemmer.prototype.r_mark_yUz = TurkishStemmer.prototype.r_mark_yUz$;

function TurkishStemmer$r_mark_yUz$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_14, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true);
};

TurkishStemmer.r_mark_yUz$LTurkishStemmer$ = TurkishStemmer$r_mark_yUz$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_sUnUz$ = function () {
	return (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_15, 4) === 0 ? false : true);
};

TurkishStemmer.prototype.r_mark_sUnUz = TurkishStemmer.prototype.r_mark_sUnUz$;

function TurkishStemmer$r_mark_sUnUz$LTurkishStemmer$($this) {
	return (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_15, 4) === 0 ? false : true);
};

TurkishStemmer.r_mark_sUnUz$LTurkishStemmer$ = TurkishStemmer$r_mark_sUnUz$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_lAr$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true);
};

TurkishStemmer.prototype.r_mark_lAr = TurkishStemmer.prototype.r_mark_lAr$;

function TurkishStemmer$r_mark_lAr$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true);
};

TurkishStemmer.r_mark_lAr$LTurkishStemmer$ = TurkishStemmer$r_mark_lAr$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_nUz$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_17, 4) === 0 ? false : true);
};

TurkishStemmer.prototype.r_mark_nUz = TurkishStemmer.prototype.r_mark_nUz$;

function TurkishStemmer$r_mark_nUz$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_17, 4) === 0 ? false : true);
};

TurkishStemmer.r_mark_nUz$LTurkishStemmer$ = TurkishStemmer$r_mark_nUz$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_DUr$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_18, 8) === 0 ? false : true);
};

TurkishStemmer.prototype.r_mark_DUr = TurkishStemmer.prototype.r_mark_DUr$;

function TurkishStemmer$r_mark_DUr$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_18, 8) === 0 ? false : true);
};

TurkishStemmer.r_mark_DUr$LTurkishStemmer$ = TurkishStemmer$r_mark_DUr$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_cAsInA$ = function () {
	return (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_19, 2) === 0 ? false : true);
};

TurkishStemmer.prototype.r_mark_cAsInA = TurkishStemmer.prototype.r_mark_cAsInA$;

function TurkishStemmer$r_mark_cAsInA$LTurkishStemmer$($this) {
	return (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_19, 2) === 0 ? false : true);
};

TurkishStemmer.r_mark_cAsInA$LTurkishStemmer$ = TurkishStemmer$r_mark_cAsInA$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_yDU$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_20, 32) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true);
};

TurkishStemmer.prototype.r_mark_yDU = TurkishStemmer.prototype.r_mark_yDU$;

function TurkishStemmer$r_mark_yDU$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_20, 32) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true);
};

TurkishStemmer.r_mark_yDU$LTurkishStemmer$ = TurkishStemmer$r_mark_yDU$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_ysA$ = function () {
	return (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_21, 8) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true);
};

TurkishStemmer.prototype.r_mark_ysA = TurkishStemmer.prototype.r_mark_ysA$;

function TurkishStemmer$r_mark_ysA$LTurkishStemmer$($this) {
	return (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_21, 8) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true);
};

TurkishStemmer.r_mark_ysA$LTurkishStemmer$ = TurkishStemmer$r_mark_ysA$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_ymUs_$ = function () {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_22, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true);
};

TurkishStemmer.prototype.r_mark_ymUs_ = TurkishStemmer.prototype.r_mark_ymUs_$;

function TurkishStemmer$r_mark_ymUs_$LTurkishStemmer$($this) {
	return (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_22, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true);
};

TurkishStemmer.r_mark_ymUs_$LTurkishStemmer$ = TurkishStemmer$r_mark_ymUs_$LTurkishStemmer$;

TurkishStemmer.prototype.r_mark_yken$ = function () {
	return (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 3, "ken") ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true);
};

TurkishStemmer.prototype.r_mark_yken = TurkishStemmer.prototype.r_mark_yken$;

function TurkishStemmer$r_mark_yken$LTurkishStemmer$($this) {
	return (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 3, "ken") ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true);
};

TurkishStemmer.r_mark_yken$LTurkishStemmer$ = TurkishStemmer$r_mark_yken$LTurkishStemmer$;

TurkishStemmer.prototype.r_stem_nominal_verb_suffixes$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_9;
	var v_10;
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
	var lab10;
	var lab11;
	var lab12;
	var lab13;
	var lab14;
	var lab15;
	var lab16;
	var lab17;
	var lab18;
	var lab19;
	var lab20;
	var lab21;
	var lab22;
	var lab23;
	var lab24;
	var lab25;
	var lab26;
	var lab27;
	var lab28;
	var lab29;
	var lab30;
	var lab31;
	var lab32;
	var lab33;
	var lab34;
	this.ket = this.cursor;
	this.B_continue_stemming_noun_suffixes = true;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = ((this.limit - this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			lab2 = true;
		lab2:
			while (lab2 === true) {
				lab2 = false;
				v_2 = ((this.limit - this.cursor) | 0);
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_22, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
						break lab3;
					}
					break lab2;
				}
				this.cursor = ((this.limit - v_2) | 0);
				lab4 = true;
			lab4:
				while (lab4 === true) {
					lab4 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_20, 32) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
						break lab4;
					}
					break lab2;
				}
				this.cursor = ((this.limit - v_2) | 0);
				lab5 = true;
			lab5:
				while (lab5 === true) {
					lab5 = false;
					if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_21, 8) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
						break lab5;
					}
					break lab2;
				}
				this.cursor = ((this.limit - v_2) | 0);
				if (! (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 3, "ken") ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
					break lab1;
				}
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		lab6 = true;
	lab6:
		while (lab6 === true) {
			lab6 = false;
			if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_19, 2) === 0 ? false : true)) {
				break lab6;
			}
			lab7 = true;
		lab7:
			while (lab7 === true) {
				lab7 = false;
				v_3 = ((this.limit - this.cursor) | 0);
				lab8 = true;
			lab8:
				while (lab8 === true) {
					lab8 = false;
					if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_15, 4) === 0 ? false : true)) {
						break lab8;
					}
					break lab7;
				}
				this.cursor = ((this.limit - v_3) | 0);
				lab9 = true;
			lab9:
				while (lab9 === true) {
					lab9 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
						break lab9;
					}
					break lab7;
				}
				this.cursor = ((this.limit - v_3) | 0);
				lab10 = true;
			lab10:
				while (lab10 === true) {
					lab10 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_12, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
						break lab10;
					}
					break lab7;
				}
				this.cursor = ((this.limit - v_3) | 0);
				lab11 = true;
			lab11:
				while (lab11 === true) {
					lab11 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_13, 4) === 0 ? false : true)) {
						break lab11;
					}
					break lab7;
				}
				this.cursor = ((this.limit - v_3) | 0);
				lab12 = true;
			lab12:
				while (lab12 === true) {
					lab12 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_14, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
						break lab12;
					}
					break lab7;
				}
				this.cursor = ((this.limit - v_3) | 0);
			}
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_22, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
				break lab6;
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		lab13 = true;
	lab13:
		while (lab13 === true) {
			lab13 = false;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
				break lab13;
			}
			this.bra = this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
			v_4 = ((this.limit - this.cursor) | 0);
			lab14 = true;
		lab14:
			while (lab14 === true) {
				lab14 = false;
				this.ket = this.cursor;
				lab15 = true;
			lab15:
				while (lab15 === true) {
					lab15 = false;
					v_5 = ((this.limit - this.cursor) | 0);
					lab16 = true;
				lab16:
					while (lab16 === true) {
						lab16 = false;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_18, 8) === 0 ? false : true)) {
							break lab16;
						}
						break lab15;
					}
					this.cursor = ((this.limit - v_5) | 0);
					lab17 = true;
				lab17:
					while (lab17 === true) {
						lab17 = false;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_20, 32) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
							break lab17;
						}
						break lab15;
					}
					this.cursor = ((this.limit - v_5) | 0);
					lab18 = true;
				lab18:
					while (lab18 === true) {
						lab18 = false;
						if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_21, 8) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
							break lab18;
						}
						break lab15;
					}
					this.cursor = ((this.limit - v_5) | 0);
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_22, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
						this.cursor = ((this.limit - v_4) | 0);
						break lab14;
					}
				}
			}
			this.B_continue_stemming_noun_suffixes = false;
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		lab19 = true;
	lab19:
		while (lab19 === true) {
			lab19 = false;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_17, 4) === 0 ? false : true)) {
				break lab19;
			}
			lab20 = true;
		lab20:
			while (lab20 === true) {
				lab20 = false;
				v_6 = ((this.limit - this.cursor) | 0);
				lab21 = true;
			lab21:
				while (lab21 === true) {
					lab21 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_20, 32) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
						break lab21;
					}
					break lab20;
				}
				this.cursor = ((this.limit - v_6) | 0);
				if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_21, 8) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
					break lab19;
				}
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		lab22 = true;
	lab22:
		while (lab22 === true) {
			lab22 = false;
			lab23 = true;
		lab23:
			while (lab23 === true) {
				lab23 = false;
				v_7 = ((this.limit - this.cursor) | 0);
				lab24 = true;
			lab24:
				while (lab24 === true) {
					lab24 = false;
					if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_15, 4) === 0 ? false : true)) {
						break lab24;
					}
					break lab23;
				}
				this.cursor = ((this.limit - v_7) | 0);
				lab25 = true;
			lab25:
				while (lab25 === true) {
					lab25 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_14, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
						break lab25;
					}
					break lab23;
				}
				this.cursor = ((this.limit - v_7) | 0);
				lab26 = true;
			lab26:
				while (lab26 === true) {
					lab26 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_13, 4) === 0 ? false : true)) {
						break lab26;
					}
					break lab23;
				}
				this.cursor = ((this.limit - v_7) | 0);
				if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_12, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
					break lab22;
				}
			}
			this.bra = this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
			v_8 = ((this.limit - this.cursor) | 0);
			lab27 = true;
		lab27:
			while (lab27 === true) {
				lab27 = false;
				this.ket = this.cursor;
				if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_22, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
					this.cursor = ((this.limit - v_8) | 0);
					break lab27;
				}
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_18, 8) === 0 ? false : true)) {
			return false;
		}
		this.bra = this.cursor;
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		v_9 = ((this.limit - this.cursor) | 0);
		lab28 = true;
	lab28:
		while (lab28 === true) {
			lab28 = false;
			this.ket = this.cursor;
			lab29 = true;
		lab29:
			while (lab29 === true) {
				lab29 = false;
				v_10 = ((this.limit - this.cursor) | 0);
				lab30 = true;
			lab30:
				while (lab30 === true) {
					lab30 = false;
					if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_15, 4) === 0 ? false : true)) {
						break lab30;
					}
					break lab29;
				}
				this.cursor = ((this.limit - v_10) | 0);
				lab31 = true;
			lab31:
				while (lab31 === true) {
					lab31 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
						break lab31;
					}
					break lab29;
				}
				this.cursor = ((this.limit - v_10) | 0);
				lab32 = true;
			lab32:
				while (lab32 === true) {
					lab32 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_12, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
						break lab32;
					}
					break lab29;
				}
				this.cursor = ((this.limit - v_10) | 0);
				lab33 = true;
			lab33:
				while (lab33 === true) {
					lab33 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_13, 4) === 0 ? false : true)) {
						break lab33;
					}
					break lab29;
				}
				this.cursor = ((this.limit - v_10) | 0);
				lab34 = true;
			lab34:
				while (lab34 === true) {
					lab34 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_14, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
						break lab34;
					}
					break lab29;
				}
				this.cursor = ((this.limit - v_10) | 0);
			}
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_22, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
				this.cursor = ((this.limit - v_9) | 0);
				break lab28;
			}
		}
	}
	this.bra = this.cursor;
	return (! BaseStemmer$slice_from$LBaseStemmer$S(this, "") ? false : true);
};

TurkishStemmer.prototype.r_stem_nominal_verb_suffixes = TurkishStemmer.prototype.r_stem_nominal_verb_suffixes$;

function TurkishStemmer$r_stem_nominal_verb_suffixes$LTurkishStemmer$($this) {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_9;
	var v_10;
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
	var lab10;
	var lab11;
	var lab12;
	var lab13;
	var lab14;
	var lab15;
	var lab16;
	var lab17;
	var lab18;
	var lab19;
	var lab20;
	var lab21;
	var lab22;
	var lab23;
	var lab24;
	var lab25;
	var lab26;
	var lab27;
	var lab28;
	var lab29;
	var lab30;
	var lab31;
	var lab32;
	var lab33;
	var lab34;
	$this.ket = $this.cursor;
	$this.B_continue_stemming_noun_suffixes = true;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = (($this.limit - $this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			lab2 = true;
		lab2:
			while (lab2 === true) {
				lab2 = false;
				v_2 = (($this.limit - $this.cursor) | 0);
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_22, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
						break lab3;
					}
					break lab2;
				}
				$this.cursor = (($this.limit - v_2) | 0);
				lab4 = true;
			lab4:
				while (lab4 === true) {
					lab4 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_20, 32) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
						break lab4;
					}
					break lab2;
				}
				$this.cursor = (($this.limit - v_2) | 0);
				lab5 = true;
			lab5:
				while (lab5 === true) {
					lab5 = false;
					if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_21, 8) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
						break lab5;
					}
					break lab2;
				}
				$this.cursor = (($this.limit - v_2) | 0);
				if (! (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 3, "ken") ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
					break lab1;
				}
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		lab6 = true;
	lab6:
		while (lab6 === true) {
			lab6 = false;
			if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_19, 2) === 0 ? false : true)) {
				break lab6;
			}
			lab7 = true;
		lab7:
			while (lab7 === true) {
				lab7 = false;
				v_3 = (($this.limit - $this.cursor) | 0);
				lab8 = true;
			lab8:
				while (lab8 === true) {
					lab8 = false;
					if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_15, 4) === 0 ? false : true)) {
						break lab8;
					}
					break lab7;
				}
				$this.cursor = (($this.limit - v_3) | 0);
				lab9 = true;
			lab9:
				while (lab9 === true) {
					lab9 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
						break lab9;
					}
					break lab7;
				}
				$this.cursor = (($this.limit - v_3) | 0);
				lab10 = true;
			lab10:
				while (lab10 === true) {
					lab10 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_12, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
						break lab10;
					}
					break lab7;
				}
				$this.cursor = (($this.limit - v_3) | 0);
				lab11 = true;
			lab11:
				while (lab11 === true) {
					lab11 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_13, 4) === 0 ? false : true)) {
						break lab11;
					}
					break lab7;
				}
				$this.cursor = (($this.limit - v_3) | 0);
				lab12 = true;
			lab12:
				while (lab12 === true) {
					lab12 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_14, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
						break lab12;
					}
					break lab7;
				}
				$this.cursor = (($this.limit - v_3) | 0);
			}
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_22, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
				break lab6;
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		lab13 = true;
	lab13:
		while (lab13 === true) {
			lab13 = false;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
				break lab13;
			}
			$this.bra = $this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
			v_4 = (($this.limit - $this.cursor) | 0);
			lab14 = true;
		lab14:
			while (lab14 === true) {
				lab14 = false;
				$this.ket = $this.cursor;
				lab15 = true;
			lab15:
				while (lab15 === true) {
					lab15 = false;
					v_5 = (($this.limit - $this.cursor) | 0);
					lab16 = true;
				lab16:
					while (lab16 === true) {
						lab16 = false;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_18, 8) === 0 ? false : true)) {
							break lab16;
						}
						break lab15;
					}
					$this.cursor = (($this.limit - v_5) | 0);
					lab17 = true;
				lab17:
					while (lab17 === true) {
						lab17 = false;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_20, 32) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
							break lab17;
						}
						break lab15;
					}
					$this.cursor = (($this.limit - v_5) | 0);
					lab18 = true;
				lab18:
					while (lab18 === true) {
						lab18 = false;
						if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_21, 8) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
							break lab18;
						}
						break lab15;
					}
					$this.cursor = (($this.limit - v_5) | 0);
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_22, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
						$this.cursor = (($this.limit - v_4) | 0);
						break lab14;
					}
				}
			}
			$this.B_continue_stemming_noun_suffixes = false;
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		lab19 = true;
	lab19:
		while (lab19 === true) {
			lab19 = false;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_17, 4) === 0 ? false : true)) {
				break lab19;
			}
			lab20 = true;
		lab20:
			while (lab20 === true) {
				lab20 = false;
				v_6 = (($this.limit - $this.cursor) | 0);
				lab21 = true;
			lab21:
				while (lab21 === true) {
					lab21 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_20, 32) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
						break lab21;
					}
					break lab20;
				}
				$this.cursor = (($this.limit - v_6) | 0);
				if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_21, 8) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
					break lab19;
				}
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		lab22 = true;
	lab22:
		while (lab22 === true) {
			lab22 = false;
			lab23 = true;
		lab23:
			while (lab23 === true) {
				lab23 = false;
				v_7 = (($this.limit - $this.cursor) | 0);
				lab24 = true;
			lab24:
				while (lab24 === true) {
					lab24 = false;
					if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_15, 4) === 0 ? false : true)) {
						break lab24;
					}
					break lab23;
				}
				$this.cursor = (($this.limit - v_7) | 0);
				lab25 = true;
			lab25:
				while (lab25 === true) {
					lab25 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_14, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
						break lab25;
					}
					break lab23;
				}
				$this.cursor = (($this.limit - v_7) | 0);
				lab26 = true;
			lab26:
				while (lab26 === true) {
					lab26 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_13, 4) === 0 ? false : true)) {
						break lab26;
					}
					break lab23;
				}
				$this.cursor = (($this.limit - v_7) | 0);
				if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_12, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
					break lab22;
				}
			}
			$this.bra = $this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
			v_8 = (($this.limit - $this.cursor) | 0);
			lab27 = true;
		lab27:
			while (lab27 === true) {
				lab27 = false;
				$this.ket = $this.cursor;
				if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_22, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
					$this.cursor = (($this.limit - v_8) | 0);
					break lab27;
				}
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_18, 8) === 0 ? false : true)) {
			return false;
		}
		$this.bra = $this.cursor;
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		v_9 = (($this.limit - $this.cursor) | 0);
		lab28 = true;
	lab28:
		while (lab28 === true) {
			lab28 = false;
			$this.ket = $this.cursor;
			lab29 = true;
		lab29:
			while (lab29 === true) {
				lab29 = false;
				v_10 = (($this.limit - $this.cursor) | 0);
				lab30 = true;
			lab30:
				while (lab30 === true) {
					lab30 = false;
					if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_15, 4) === 0 ? false : true)) {
						break lab30;
					}
					break lab29;
				}
				$this.cursor = (($this.limit - v_10) | 0);
				lab31 = true;
			lab31:
				while (lab31 === true) {
					lab31 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
						break lab31;
					}
					break lab29;
				}
				$this.cursor = (($this.limit - v_10) | 0);
				lab32 = true;
			lab32:
				while (lab32 === true) {
					lab32 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_12, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
						break lab32;
					}
					break lab29;
				}
				$this.cursor = (($this.limit - v_10) | 0);
				lab33 = true;
			lab33:
				while (lab33 === true) {
					lab33 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_13, 4) === 0 ? false : true)) {
						break lab33;
					}
					break lab29;
				}
				$this.cursor = (($this.limit - v_10) | 0);
				lab34 = true;
			lab34:
				while (lab34 === true) {
					lab34 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_14, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
						break lab34;
					}
					break lab29;
				}
				$this.cursor = (($this.limit - v_10) | 0);
			}
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_22, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
				$this.cursor = (($this.limit - v_9) | 0);
				break lab28;
			}
		}
	}
	$this.bra = $this.cursor;
	return (! BaseStemmer$slice_from$LBaseStemmer$S($this, "") ? false : true);
};

TurkishStemmer.r_stem_nominal_verb_suffixes$LTurkishStemmer$ = TurkishStemmer$r_stem_nominal_verb_suffixes$LTurkishStemmer$;

TurkishStemmer.prototype.r_stem_suffix_chain_before_ki$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_9;
	var v_10;
	var v_11;
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
	var lab10;
	var lab11;
	var lab12;
	var lab13;
	var lab14;
	var lab15;
	var lab16;
	var lab17;
	var lab18;
	this.ket = this.cursor;
	if (! (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 2, "ki") ? false : true)) {
		return false;
	}
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = ((this.limit - this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_6, 4) === 0 ? false : true)) {
				break lab1;
			}
			this.bra = this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
			v_2 = ((this.limit - this.cursor) | 0);
			lab2 = true;
		lab2:
			while (lab2 === true) {
				lab2 = false;
				this.ket = this.cursor;
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					v_3 = ((this.limit - this.cursor) | 0);
					lab4 = true;
				lab4:
					while (lab4 === true) {
						lab4 = false;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
							break lab4;
						}
						this.bra = this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						v_4 = ((this.limit - this.cursor) | 0);
						lab5 = true;
					lab5:
						while (lab5 === true) {
							lab5 = false;
							if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
								this.cursor = ((this.limit - v_4) | 0);
								break lab5;
							}
						}
						break lab3;
					}
					this.cursor = ((this.limit - v_3) | 0);
					if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$(this) ? false : true)) {
						this.cursor = ((this.limit - v_2) | 0);
						break lab2;
					}
					this.bra = this.cursor;
					if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
						return false;
					}
					v_5 = ((this.limit - this.cursor) | 0);
					lab6 = true;
				lab6:
					while (lab6 === true) {
						lab6 = false;
						this.ket = this.cursor;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
							this.cursor = ((this.limit - v_5) | 0);
							break lab6;
						}
						this.bra = this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
							this.cursor = ((this.limit - v_5) | 0);
							break lab6;
						}
					}
				}
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		lab7 = true;
	lab7:
		while (lab7 === true) {
			lab7 = false;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_3, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_n_consonant$LTurkishStemmer$(this) ? false : true)) {
				break lab7;
			}
			this.bra = this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
			v_6 = ((this.limit - this.cursor) | 0);
			lab8 = true;
		lab8:
			while (lab8 === true) {
				lab8 = false;
				this.ket = this.cursor;
				lab9 = true;
			lab9:
				while (lab9 === true) {
					lab9 = false;
					v_7 = ((this.limit - this.cursor) | 0);
					lab10 = true;
				lab10:
					while (lab10 === true) {
						lab10 = false;
						if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_1, 2) === 0 ? false : true)) {
							break lab10;
						}
						this.bra = this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						break lab9;
					}
					this.cursor = ((this.limit - v_7) | 0);
					lab11 = true;
				lab11:
					while (lab11 === true) {
						lab11 = false;
						this.ket = this.cursor;
						lab12 = true;
					lab12:
						while (lab12 === true) {
							lab12 = false;
							v_8 = ((this.limit - this.cursor) | 0);
							lab13 = true;
						lab13:
							while (lab13 === true) {
								lab13 = false;
								if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$(this) ? false : true)) {
									break lab13;
								}
								break lab12;
							}
							this.cursor = ((this.limit - v_8) | 0);
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$(this) ? false : true)) {
								break lab11;
							}
						}
						this.bra = this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						v_9 = ((this.limit - this.cursor) | 0);
						lab14 = true;
					lab14:
						while (lab14 === true) {
							lab14 = false;
							this.ket = this.cursor;
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
								this.cursor = ((this.limit - v_9) | 0);
								break lab14;
							}
							this.bra = this.cursor;
							if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
								return false;
							}
							if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
								this.cursor = ((this.limit - v_9) | 0);
								break lab14;
							}
						}
						break lab9;
					}
					this.cursor = ((this.limit - v_7) | 0);
					if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
						this.cursor = ((this.limit - v_6) | 0);
						break lab8;
					}
				}
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_7, 2) === 0 ? false : true)) {
			return false;
		}
		lab15 = true;
	lab15:
		while (lab15 === true) {
			lab15 = false;
			v_10 = ((this.limit - this.cursor) | 0);
			lab16 = true;
		lab16:
			while (lab16 === true) {
				lab16 = false;
				if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_1, 2) === 0 ? false : true)) {
					break lab16;
				}
				this.bra = this.cursor;
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
					return false;
				}
				break lab15;
			}
			this.cursor = ((this.limit - v_10) | 0);
			lab17 = true;
		lab17:
			while (lab17 === true) {
				lab17 = false;
				if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$(this) ? false : true)) {
					break lab17;
				}
				this.bra = this.cursor;
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
					return false;
				}
				v_11 = ((this.limit - this.cursor) | 0);
				lab18 = true;
			lab18:
				while (lab18 === true) {
					lab18 = false;
					this.ket = this.cursor;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
						this.cursor = ((this.limit - v_11) | 0);
						break lab18;
					}
					this.bra = this.cursor;
					if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
						return false;
					}
					if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
						this.cursor = ((this.limit - v_11) | 0);
						break lab18;
					}
				}
				break lab15;
			}
			this.cursor = ((this.limit - v_10) | 0);
			if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
				return false;
			}
		}
	}
	return true;
};

TurkishStemmer.prototype.r_stem_suffix_chain_before_ki = TurkishStemmer.prototype.r_stem_suffix_chain_before_ki$;

function TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this) {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_9;
	var v_10;
	var v_11;
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
	var lab10;
	var lab11;
	var lab12;
	var lab13;
	var lab14;
	var lab15;
	var lab16;
	var lab17;
	var lab18;
	$this.ket = $this.cursor;
	if (! (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 2, "ki") ? false : true)) {
		return false;
	}
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = (($this.limit - $this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_6, 4) === 0 ? false : true)) {
				break lab1;
			}
			$this.bra = $this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
			v_2 = (($this.limit - $this.cursor) | 0);
			lab2 = true;
		lab2:
			while (lab2 === true) {
				lab2 = false;
				$this.ket = $this.cursor;
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					v_3 = (($this.limit - $this.cursor) | 0);
					lab4 = true;
				lab4:
					while (lab4 === true) {
						lab4 = false;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
							break lab4;
						}
						$this.bra = $this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						v_4 = (($this.limit - $this.cursor) | 0);
						lab5 = true;
					lab5:
						while (lab5 === true) {
							lab5 = false;
							if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
								$this.cursor = (($this.limit - v_4) | 0);
								break lab5;
							}
						}
						break lab3;
					}
					$this.cursor = (($this.limit - v_3) | 0);
					if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$($this) ? false : true)) {
						$this.cursor = (($this.limit - v_2) | 0);
						break lab2;
					}
					$this.bra = $this.cursor;
					if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
						return false;
					}
					v_5 = (($this.limit - $this.cursor) | 0);
					lab6 = true;
				lab6:
					while (lab6 === true) {
						lab6 = false;
						$this.ket = $this.cursor;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
							$this.cursor = (($this.limit - v_5) | 0);
							break lab6;
						}
						$this.bra = $this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
							$this.cursor = (($this.limit - v_5) | 0);
							break lab6;
						}
					}
				}
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		lab7 = true;
	lab7:
		while (lab7 === true) {
			lab7 = false;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_3, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_n_consonant$LTurkishStemmer$($this) ? false : true)) {
				break lab7;
			}
			$this.bra = $this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
			v_6 = (($this.limit - $this.cursor) | 0);
			lab8 = true;
		lab8:
			while (lab8 === true) {
				lab8 = false;
				$this.ket = $this.cursor;
				lab9 = true;
			lab9:
				while (lab9 === true) {
					lab9 = false;
					v_7 = (($this.limit - $this.cursor) | 0);
					lab10 = true;
				lab10:
					while (lab10 === true) {
						lab10 = false;
						if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_1, 2) === 0 ? false : true)) {
							break lab10;
						}
						$this.bra = $this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						break lab9;
					}
					$this.cursor = (($this.limit - v_7) | 0);
					lab11 = true;
				lab11:
					while (lab11 === true) {
						lab11 = false;
						$this.ket = $this.cursor;
						lab12 = true;
					lab12:
						while (lab12 === true) {
							lab12 = false;
							v_8 = (($this.limit - $this.cursor) | 0);
							lab13 = true;
						lab13:
							while (lab13 === true) {
								lab13 = false;
								if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$($this) ? false : true)) {
									break lab13;
								}
								break lab12;
							}
							$this.cursor = (($this.limit - v_8) | 0);
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$($this) ? false : true)) {
								break lab11;
							}
						}
						$this.bra = $this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						v_9 = (($this.limit - $this.cursor) | 0);
						lab14 = true;
					lab14:
						while (lab14 === true) {
							lab14 = false;
							$this.ket = $this.cursor;
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
								$this.cursor = (($this.limit - v_9) | 0);
								break lab14;
							}
							$this.bra = $this.cursor;
							if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
								return false;
							}
							if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
								$this.cursor = (($this.limit - v_9) | 0);
								break lab14;
							}
						}
						break lab9;
					}
					$this.cursor = (($this.limit - v_7) | 0);
					if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
						$this.cursor = (($this.limit - v_6) | 0);
						break lab8;
					}
				}
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_7, 2) === 0 ? false : true)) {
			return false;
		}
		lab15 = true;
	lab15:
		while (lab15 === true) {
			lab15 = false;
			v_10 = (($this.limit - $this.cursor) | 0);
			lab16 = true;
		lab16:
			while (lab16 === true) {
				lab16 = false;
				if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_1, 2) === 0 ? false : true)) {
					break lab16;
				}
				$this.bra = $this.cursor;
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
					return false;
				}
				break lab15;
			}
			$this.cursor = (($this.limit - v_10) | 0);
			lab17 = true;
		lab17:
			while (lab17 === true) {
				lab17 = false;
				if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$($this) ? false : true)) {
					break lab17;
				}
				$this.bra = $this.cursor;
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
					return false;
				}
				v_11 = (($this.limit - $this.cursor) | 0);
				lab18 = true;
			lab18:
				while (lab18 === true) {
					lab18 = false;
					$this.ket = $this.cursor;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
						$this.cursor = (($this.limit - v_11) | 0);
						break lab18;
					}
					$this.bra = $this.cursor;
					if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
						return false;
					}
					if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
						$this.cursor = (($this.limit - v_11) | 0);
						break lab18;
					}
				}
				break lab15;
			}
			$this.cursor = (($this.limit - v_10) | 0);
			if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
				return false;
			}
		}
	}
	return true;
};

TurkishStemmer.r_stem_suffix_chain_before_ki$LTurkishStemmer$ = TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$;

TurkishStemmer.prototype.r_stem_noun_suffixes$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_9;
	var v_10;
	var v_11;
	var v_12;
	var v_13;
	var v_14;
	var v_15;
	var v_16;
	var v_17;
	var v_18;
	var v_19;
	var v_20;
	var v_21;
	var v_22;
	var v_23;
	var v_24;
	var v_25;
	var v_26;
	var v_27;
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
	var lab10;
	var lab11;
	var lab12;
	var lab13;
	var lab14;
	var lab15;
	var lab16;
	var lab17;
	var lab18;
	var lab19;
	var lab20;
	var lab21;
	var lab22;
	var lab23;
	var lab24;
	var lab25;
	var lab26;
	var lab27;
	var lab28;
	var lab29;
	var lab30;
	var lab31;
	var lab32;
	var lab33;
	var lab34;
	var lab35;
	var lab36;
	var lab37;
	var lab38;
	var lab39;
	var lab40;
	var lab41;
	var lab42;
	var lab43;
	var lab44;
	var lab45;
	var lab46;
	var lab47;
	var lab48;
	var lab49;
	var lab50;
	var lab51;
	var lab52;
	var lab53;
	var cursor$0;
	var cursor$1;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = ((this.limit - this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			this.ket = this.cursor;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
				break lab1;
			}
			this.bra = this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
			v_2 = ((this.limit - this.cursor) | 0);
			lab2 = true;
		lab2:
			while (lab2 === true) {
				lab2 = false;
				if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
					this.cursor = ((this.limit - v_2) | 0);
					break lab2;
				}
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			this.ket = this.cursor;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_11, 2) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_n_consonant$LTurkishStemmer$(this) ? false : true)) {
				break lab3;
			}
			this.bra = this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
			v_3 = ((this.limit - this.cursor) | 0);
			lab4 = true;
		lab4:
			while (lab4 === true) {
				lab4 = false;
				lab5 = true;
			lab5:
				while (lab5 === true) {
					lab5 = false;
					v_4 = ((this.limit - this.cursor) | 0);
					lab6 = true;
				lab6:
					while (lab6 === true) {
						lab6 = false;
						this.ket = this.cursor;
						if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_1, 2) === 0 ? false : true)) {
							break lab6;
						}
						this.bra = this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						break lab5;
					}
					this.cursor = ((this.limit - v_4) | 0);
					lab7 = true;
				lab7:
					while (lab7 === true) {
						lab7 = false;
						this.ket = this.cursor;
						lab8 = true;
					lab8:
						while (lab8 === true) {
							lab8 = false;
							v_5 = ((this.limit - this.cursor) | 0);
							lab9 = true;
						lab9:
							while (lab9 === true) {
								lab9 = false;
								if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$(this) ? false : true)) {
									break lab9;
								}
								break lab8;
							}
							this.cursor = ((this.limit - v_5) | 0);
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$(this) ? false : true)) {
								break lab7;
							}
						}
						this.bra = this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						v_6 = ((this.limit - this.cursor) | 0);
						lab10 = true;
					lab10:
						while (lab10 === true) {
							lab10 = false;
							this.ket = this.cursor;
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
								this.cursor = ((this.limit - v_6) | 0);
								break lab10;
							}
							this.bra = this.cursor;
							if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
								return false;
							}
							if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
								this.cursor = ((this.limit - v_6) | 0);
								break lab10;
							}
						}
						break lab5;
					}
					cursor$0 = this.cursor = ((this.limit - v_4) | 0);
					this.ket = cursor$0;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
						this.cursor = ((this.limit - v_3) | 0);
						break lab4;
					}
					this.bra = this.cursor;
					if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
						return false;
					}
					if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
						this.cursor = ((this.limit - v_3) | 0);
						break lab4;
					}
				}
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		lab11 = true;
	lab11:
		while (lab11 === true) {
			lab11 = false;
			this.ket = this.cursor;
			lab12 = true;
		lab12:
			while (lab12 === true) {
				lab12 = false;
				v_7 = ((this.limit - this.cursor) | 0);
				lab13 = true;
			lab13:
				while (lab13 === true) {
					lab13 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_7, 2) === 0 ? false : true)) {
						break lab13;
					}
					break lab12;
				}
				this.cursor = ((this.limit - v_7) | 0);
				if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_5, 2) === 0 ? false : true)) {
					break lab11;
				}
			}
			lab14 = true;
		lab14:
			while (lab14 === true) {
				lab14 = false;
				v_8 = ((this.limit - this.cursor) | 0);
				lab15 = true;
			lab15:
				while (lab15 === true) {
					lab15 = false;
					if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_1, 2) === 0 ? false : true)) {
						break lab15;
					}
					this.bra = this.cursor;
					if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
						return false;
					}
					break lab14;
				}
				this.cursor = ((this.limit - v_8) | 0);
				lab16 = true;
			lab16:
				while (lab16 === true) {
					lab16 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$(this) ? false : true)) {
						break lab16;
					}
					this.bra = this.cursor;
					if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
						return false;
					}
					v_9 = ((this.limit - this.cursor) | 0);
					lab17 = true;
				lab17:
					while (lab17 === true) {
						lab17 = false;
						this.ket = this.cursor;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
							this.cursor = ((this.limit - v_9) | 0);
							break lab17;
						}
						this.bra = this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
							this.cursor = ((this.limit - v_9) | 0);
							break lab17;
						}
					}
					break lab14;
				}
				this.cursor = ((this.limit - v_8) | 0);
				if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
					break lab11;
				}
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		lab18 = true;
	lab18:
		while (lab18 === true) {
			lab18 = false;
			this.ket = this.cursor;
			lab19 = true;
		lab19:
			while (lab19 === true) {
				lab19 = false;
				v_10 = ((this.limit - this.cursor) | 0);
				lab20 = true;
			lab20:
				while (lab20 === true) {
					lab20 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_9, 2) === 0 ? false : true)) {
						break lab20;
					}
					break lab19;
				}
				this.cursor = ((this.limit - v_10) | 0);
				if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_2, 4) === 0 ? false : true)) {
					break lab18;
				}
			}
			lab21 = true;
		lab21:
			while (lab21 === true) {
				lab21 = false;
				v_11 = ((this.limit - this.cursor) | 0);
				lab22 = true;
			lab22:
				while (lab22 === true) {
					lab22 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$(this) ? false : true)) {
						break lab22;
					}
					this.bra = this.cursor;
					if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
						return false;
					}
					v_12 = ((this.limit - this.cursor) | 0);
					lab23 = true;
				lab23:
					while (lab23 === true) {
						lab23 = false;
						this.ket = this.cursor;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
							this.cursor = ((this.limit - v_12) | 0);
							break lab23;
						}
						this.bra = this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
							this.cursor = ((this.limit - v_12) | 0);
							break lab23;
						}
					}
					break lab21;
				}
				this.cursor = ((this.limit - v_11) | 0);
				if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_1, 2) === 0 ? false : true)) {
					break lab18;
				}
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		lab24 = true;
	lab24:
		while (lab24 === true) {
			lab24 = false;
			this.ket = this.cursor;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_8, 4) === 0 ? false : true)) {
				break lab24;
			}
			this.bra = this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
			v_13 = ((this.limit - this.cursor) | 0);
			lab25 = true;
		lab25:
			while (lab25 === true) {
				lab25 = false;
				this.ket = this.cursor;
				lab26 = true;
			lab26:
				while (lab26 === true) {
					lab26 = false;
					v_14 = ((this.limit - this.cursor) | 0);
					lab27 = true;
				lab27:
					while (lab27 === true) {
						lab27 = false;
						if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$(this) ? false : true)) {
							break lab27;
						}
						this.bra = this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						v_15 = ((this.limit - this.cursor) | 0);
						lab28 = true;
					lab28:
						while (lab28 === true) {
							lab28 = false;
							this.ket = this.cursor;
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
								this.cursor = ((this.limit - v_15) | 0);
								break lab28;
							}
							this.bra = this.cursor;
							if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
								return false;
							}
							if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
								this.cursor = ((this.limit - v_15) | 0);
								break lab28;
							}
						}
						break lab26;
					}
					this.cursor = ((this.limit - v_14) | 0);
					lab29 = true;
				lab29:
					while (lab29 === true) {
						lab29 = false;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
							break lab29;
						}
						this.bra = this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						v_16 = ((this.limit - this.cursor) | 0);
						lab30 = true;
					lab30:
						while (lab30 === true) {
							lab30 = false;
							if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
								this.cursor = ((this.limit - v_16) | 0);
								break lab30;
							}
						}
						break lab26;
					}
					this.cursor = ((this.limit - v_14) | 0);
					if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
						this.cursor = ((this.limit - v_13) | 0);
						break lab25;
					}
				}
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		lab31 = true;
	lab31:
		while (lab31 === true) {
			lab31 = false;
			this.ket = this.cursor;
			lab32 = true;
		lab32:
			while (lab32 === true) {
				lab32 = false;
				v_17 = ((this.limit - this.cursor) | 0);
				lab33 = true;
			lab33:
				while (lab33 === true) {
					lab33 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_3, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_n_consonant$LTurkishStemmer$(this) ? false : true)) {
						break lab33;
					}
					break lab32;
				}
				this.cursor = ((this.limit - v_17) | 0);
				if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_10, 2) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
					break lab31;
				}
			}
			this.bra = this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
			v_18 = ((this.limit - this.cursor) | 0);
			lab34 = true;
		lab34:
			while (lab34 === true) {
				lab34 = false;
				lab35 = true;
			lab35:
				while (lab35 === true) {
					lab35 = false;
					v_19 = ((this.limit - this.cursor) | 0);
					lab36 = true;
				lab36:
					while (lab36 === true) {
						lab36 = false;
						this.ket = this.cursor;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
							break lab36;
						}
						this.bra = this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
							break lab36;
						}
						break lab35;
					}
					this.cursor = ((this.limit - v_19) | 0);
					lab37 = true;
				lab37:
					while (lab37 === true) {
						lab37 = false;
						this.ket = this.cursor;
						lab38 = true;
					lab38:
						while (lab38 === true) {
							lab38 = false;
							v_20 = ((this.limit - this.cursor) | 0);
							lab39 = true;
						lab39:
							while (lab39 === true) {
								lab39 = false;
								if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$(this) ? false : true)) {
									break lab39;
								}
								break lab38;
							}
							this.cursor = ((this.limit - v_20) | 0);
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$(this) ? false : true)) {
								break lab37;
							}
						}
						this.bra = this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						v_21 = ((this.limit - this.cursor) | 0);
						lab40 = true;
					lab40:
						while (lab40 === true) {
							lab40 = false;
							this.ket = this.cursor;
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
								this.cursor = ((this.limit - v_21) | 0);
								break lab40;
							}
							this.bra = this.cursor;
							if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
								return false;
							}
							if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
								this.cursor = ((this.limit - v_21) | 0);
								break lab40;
							}
						}
						break lab35;
					}
					this.cursor = ((this.limit - v_19) | 0);
					if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
						this.cursor = ((this.limit - v_18) | 0);
						break lab34;
					}
				}
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		lab41 = true;
	lab41:
		while (lab41 === true) {
			lab41 = false;
			this.ket = this.cursor;
			if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_1, 2) === 0 ? false : true)) {
				break lab41;
			}
			this.bra = this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		lab42 = true;
	lab42:
		while (lab42 === true) {
			lab42 = false;
			if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
				break lab42;
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		lab43 = true;
	lab43:
		while (lab43 === true) {
			lab43 = false;
			this.ket = this.cursor;
			lab44 = true;
		lab44:
			while (lab44 === true) {
				lab44 = false;
				v_22 = ((this.limit - this.cursor) | 0);
				lab45 = true;
			lab45:
				while (lab45 === true) {
					lab45 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_6, 4) === 0 ? false : true)) {
						break lab45;
					}
					break lab44;
				}
				this.cursor = ((this.limit - v_22) | 0);
				lab46 = true;
			lab46:
				while (lab46 === true) {
					lab46 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
						break lab46;
					}
					break lab44;
				}
				this.cursor = ((this.limit - v_22) | 0);
				if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_4, 2) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$(this) ? false : true)) {
					break lab43;
				}
			}
			this.bra = this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
			v_23 = ((this.limit - this.cursor) | 0);
			lab47 = true;
		lab47:
			while (lab47 === true) {
				lab47 = false;
				this.ket = this.cursor;
				lab48 = true;
			lab48:
				while (lab48 === true) {
					lab48 = false;
					v_24 = ((this.limit - this.cursor) | 0);
					lab49 = true;
				lab49:
					while (lab49 === true) {
						lab49 = false;
						if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$(this) ? false : true)) {
							break lab49;
						}
						this.bra = this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						v_25 = ((this.limit - this.cursor) | 0);
						lab50 = true;
					lab50:
						while (lab50 === true) {
							lab50 = false;
							this.ket = this.cursor;
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
								this.cursor = ((this.limit - v_25) | 0);
								break lab50;
							}
						}
						break lab48;
					}
					this.cursor = ((this.limit - v_24) | 0);
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
						this.cursor = ((this.limit - v_23) | 0);
						break lab47;
					}
				}
				this.bra = this.cursor;
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
					return false;
				}
				this.ket = this.cursor;
				if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
					this.cursor = ((this.limit - v_23) | 0);
					break lab47;
				}
			}
			break lab0;
		}
		cursor$1 = this.cursor = ((this.limit - v_1) | 0);
		this.ket = cursor$1;
		lab51 = true;
	lab51:
		while (lab51 === true) {
			lab51 = false;
			v_26 = ((this.limit - this.cursor) | 0);
			lab52 = true;
		lab52:
			while (lab52 === true) {
				lab52 = false;
				if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$(this) ? false : true)) {
					break lab52;
				}
				break lab51;
			}
			this.cursor = ((this.limit - v_26) | 0);
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$(this) ? false : true)) {
				return false;
			}
		}
		this.bra = this.cursor;
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		v_27 = ((this.limit - this.cursor) | 0);
		lab53 = true;
	lab53:
		while (lab53 === true) {
			lab53 = false;
			this.ket = this.cursor;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$(this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
				this.cursor = ((this.limit - v_27) | 0);
				break lab53;
			}
			this.bra = this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
			if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$(this)) {
				this.cursor = ((this.limit - v_27) | 0);
				break lab53;
			}
		}
	}
	return true;
};

TurkishStemmer.prototype.r_stem_noun_suffixes = TurkishStemmer.prototype.r_stem_noun_suffixes$;

function TurkishStemmer$r_stem_noun_suffixes$LTurkishStemmer$($this) {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_9;
	var v_10;
	var v_11;
	var v_12;
	var v_13;
	var v_14;
	var v_15;
	var v_16;
	var v_17;
	var v_18;
	var v_19;
	var v_20;
	var v_21;
	var v_22;
	var v_23;
	var v_24;
	var v_25;
	var v_26;
	var v_27;
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
	var lab10;
	var lab11;
	var lab12;
	var lab13;
	var lab14;
	var lab15;
	var lab16;
	var lab17;
	var lab18;
	var lab19;
	var lab20;
	var lab21;
	var lab22;
	var lab23;
	var lab24;
	var lab25;
	var lab26;
	var lab27;
	var lab28;
	var lab29;
	var lab30;
	var lab31;
	var lab32;
	var lab33;
	var lab34;
	var lab35;
	var lab36;
	var lab37;
	var lab38;
	var lab39;
	var lab40;
	var lab41;
	var lab42;
	var lab43;
	var lab44;
	var lab45;
	var lab46;
	var lab47;
	var lab48;
	var lab49;
	var lab50;
	var lab51;
	var lab52;
	var lab53;
	var cursor$0;
	var cursor$1;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = (($this.limit - $this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			$this.ket = $this.cursor;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
				break lab1;
			}
			$this.bra = $this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
			v_2 = (($this.limit - $this.cursor) | 0);
			lab2 = true;
		lab2:
			while (lab2 === true) {
				lab2 = false;
				if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
					$this.cursor = (($this.limit - v_2) | 0);
					break lab2;
				}
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			$this.ket = $this.cursor;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_11, 2) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_n_consonant$LTurkishStemmer$($this) ? false : true)) {
				break lab3;
			}
			$this.bra = $this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
			v_3 = (($this.limit - $this.cursor) | 0);
			lab4 = true;
		lab4:
			while (lab4 === true) {
				lab4 = false;
				lab5 = true;
			lab5:
				while (lab5 === true) {
					lab5 = false;
					v_4 = (($this.limit - $this.cursor) | 0);
					lab6 = true;
				lab6:
					while (lab6 === true) {
						lab6 = false;
						$this.ket = $this.cursor;
						if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_1, 2) === 0 ? false : true)) {
							break lab6;
						}
						$this.bra = $this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						break lab5;
					}
					$this.cursor = (($this.limit - v_4) | 0);
					lab7 = true;
				lab7:
					while (lab7 === true) {
						lab7 = false;
						$this.ket = $this.cursor;
						lab8 = true;
					lab8:
						while (lab8 === true) {
							lab8 = false;
							v_5 = (($this.limit - $this.cursor) | 0);
							lab9 = true;
						lab9:
							while (lab9 === true) {
								lab9 = false;
								if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$($this) ? false : true)) {
									break lab9;
								}
								break lab8;
							}
							$this.cursor = (($this.limit - v_5) | 0);
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$($this) ? false : true)) {
								break lab7;
							}
						}
						$this.bra = $this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						v_6 = (($this.limit - $this.cursor) | 0);
						lab10 = true;
					lab10:
						while (lab10 === true) {
							lab10 = false;
							$this.ket = $this.cursor;
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
								$this.cursor = (($this.limit - v_6) | 0);
								break lab10;
							}
							$this.bra = $this.cursor;
							if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
								return false;
							}
							if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
								$this.cursor = (($this.limit - v_6) | 0);
								break lab10;
							}
						}
						break lab5;
					}
					cursor$0 = $this.cursor = (($this.limit - v_4) | 0);
					$this.ket = cursor$0;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
						$this.cursor = (($this.limit - v_3) | 0);
						break lab4;
					}
					$this.bra = $this.cursor;
					if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
						return false;
					}
					if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
						$this.cursor = (($this.limit - v_3) | 0);
						break lab4;
					}
				}
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		lab11 = true;
	lab11:
		while (lab11 === true) {
			lab11 = false;
			$this.ket = $this.cursor;
			lab12 = true;
		lab12:
			while (lab12 === true) {
				lab12 = false;
				v_7 = (($this.limit - $this.cursor) | 0);
				lab13 = true;
			lab13:
				while (lab13 === true) {
					lab13 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_7, 2) === 0 ? false : true)) {
						break lab13;
					}
					break lab12;
				}
				$this.cursor = (($this.limit - v_7) | 0);
				if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_5, 2) === 0 ? false : true)) {
					break lab11;
				}
			}
			lab14 = true;
		lab14:
			while (lab14 === true) {
				lab14 = false;
				v_8 = (($this.limit - $this.cursor) | 0);
				lab15 = true;
			lab15:
				while (lab15 === true) {
					lab15 = false;
					if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_1, 2) === 0 ? false : true)) {
						break lab15;
					}
					$this.bra = $this.cursor;
					if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
						return false;
					}
					break lab14;
				}
				$this.cursor = (($this.limit - v_8) | 0);
				lab16 = true;
			lab16:
				while (lab16 === true) {
					lab16 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$($this) ? false : true)) {
						break lab16;
					}
					$this.bra = $this.cursor;
					if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
						return false;
					}
					v_9 = (($this.limit - $this.cursor) | 0);
					lab17 = true;
				lab17:
					while (lab17 === true) {
						lab17 = false;
						$this.ket = $this.cursor;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
							$this.cursor = (($this.limit - v_9) | 0);
							break lab17;
						}
						$this.bra = $this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
							$this.cursor = (($this.limit - v_9) | 0);
							break lab17;
						}
					}
					break lab14;
				}
				$this.cursor = (($this.limit - v_8) | 0);
				if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
					break lab11;
				}
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		lab18 = true;
	lab18:
		while (lab18 === true) {
			lab18 = false;
			$this.ket = $this.cursor;
			lab19 = true;
		lab19:
			while (lab19 === true) {
				lab19 = false;
				v_10 = (($this.limit - $this.cursor) | 0);
				lab20 = true;
			lab20:
				while (lab20 === true) {
					lab20 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_9, 2) === 0 ? false : true)) {
						break lab20;
					}
					break lab19;
				}
				$this.cursor = (($this.limit - v_10) | 0);
				if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_2, 4) === 0 ? false : true)) {
					break lab18;
				}
			}
			lab21 = true;
		lab21:
			while (lab21 === true) {
				lab21 = false;
				v_11 = (($this.limit - $this.cursor) | 0);
				lab22 = true;
			lab22:
				while (lab22 === true) {
					lab22 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$($this) ? false : true)) {
						break lab22;
					}
					$this.bra = $this.cursor;
					if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
						return false;
					}
					v_12 = (($this.limit - $this.cursor) | 0);
					lab23 = true;
				lab23:
					while (lab23 === true) {
						lab23 = false;
						$this.ket = $this.cursor;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
							$this.cursor = (($this.limit - v_12) | 0);
							break lab23;
						}
						$this.bra = $this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
							$this.cursor = (($this.limit - v_12) | 0);
							break lab23;
						}
					}
					break lab21;
				}
				$this.cursor = (($this.limit - v_11) | 0);
				if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_1, 2) === 0 ? false : true)) {
					break lab18;
				}
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		lab24 = true;
	lab24:
		while (lab24 === true) {
			lab24 = false;
			$this.ket = $this.cursor;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_8, 4) === 0 ? false : true)) {
				break lab24;
			}
			$this.bra = $this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
			v_13 = (($this.limit - $this.cursor) | 0);
			lab25 = true;
		lab25:
			while (lab25 === true) {
				lab25 = false;
				$this.ket = $this.cursor;
				lab26 = true;
			lab26:
				while (lab26 === true) {
					lab26 = false;
					v_14 = (($this.limit - $this.cursor) | 0);
					lab27 = true;
				lab27:
					while (lab27 === true) {
						lab27 = false;
						if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$($this) ? false : true)) {
							break lab27;
						}
						$this.bra = $this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						v_15 = (($this.limit - $this.cursor) | 0);
						lab28 = true;
					lab28:
						while (lab28 === true) {
							lab28 = false;
							$this.ket = $this.cursor;
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
								$this.cursor = (($this.limit - v_15) | 0);
								break lab28;
							}
							$this.bra = $this.cursor;
							if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
								return false;
							}
							if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
								$this.cursor = (($this.limit - v_15) | 0);
								break lab28;
							}
						}
						break lab26;
					}
					$this.cursor = (($this.limit - v_14) | 0);
					lab29 = true;
				lab29:
					while (lab29 === true) {
						lab29 = false;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
							break lab29;
						}
						$this.bra = $this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						v_16 = (($this.limit - $this.cursor) | 0);
						lab30 = true;
					lab30:
						while (lab30 === true) {
							lab30 = false;
							if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
								$this.cursor = (($this.limit - v_16) | 0);
								break lab30;
							}
						}
						break lab26;
					}
					$this.cursor = (($this.limit - v_14) | 0);
					if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
						$this.cursor = (($this.limit - v_13) | 0);
						break lab25;
					}
				}
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		lab31 = true;
	lab31:
		while (lab31 === true) {
			lab31 = false;
			$this.ket = $this.cursor;
			lab32 = true;
		lab32:
			while (lab32 === true) {
				lab32 = false;
				v_17 = (($this.limit - $this.cursor) | 0);
				lab33 = true;
			lab33:
				while (lab33 === true) {
					lab33 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_3, 4) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_n_consonant$LTurkishStemmer$($this) ? false : true)) {
						break lab33;
					}
					break lab32;
				}
				$this.cursor = (($this.limit - v_17) | 0);
				if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_10, 2) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
					break lab31;
				}
			}
			$this.bra = $this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
			v_18 = (($this.limit - $this.cursor) | 0);
			lab34 = true;
		lab34:
			while (lab34 === true) {
				lab34 = false;
				lab35 = true;
			lab35:
				while (lab35 === true) {
					lab35 = false;
					v_19 = (($this.limit - $this.cursor) | 0);
					lab36 = true;
				lab36:
					while (lab36 === true) {
						lab36 = false;
						$this.ket = $this.cursor;
						if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
							break lab36;
						}
						$this.bra = $this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
							break lab36;
						}
						break lab35;
					}
					$this.cursor = (($this.limit - v_19) | 0);
					lab37 = true;
				lab37:
					while (lab37 === true) {
						lab37 = false;
						$this.ket = $this.cursor;
						lab38 = true;
					lab38:
						while (lab38 === true) {
							lab38 = false;
							v_20 = (($this.limit - $this.cursor) | 0);
							lab39 = true;
						lab39:
							while (lab39 === true) {
								lab39 = false;
								if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$($this) ? false : true)) {
									break lab39;
								}
								break lab38;
							}
							$this.cursor = (($this.limit - v_20) | 0);
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$($this) ? false : true)) {
								break lab37;
							}
						}
						$this.bra = $this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						v_21 = (($this.limit - $this.cursor) | 0);
						lab40 = true;
					lab40:
						while (lab40 === true) {
							lab40 = false;
							$this.ket = $this.cursor;
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
								$this.cursor = (($this.limit - v_21) | 0);
								break lab40;
							}
							$this.bra = $this.cursor;
							if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
								return false;
							}
							if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
								$this.cursor = (($this.limit - v_21) | 0);
								break lab40;
							}
						}
						break lab35;
					}
					$this.cursor = (($this.limit - v_19) | 0);
					if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
						$this.cursor = (($this.limit - v_18) | 0);
						break lab34;
					}
				}
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		lab41 = true;
	lab41:
		while (lab41 === true) {
			lab41 = false;
			$this.ket = $this.cursor;
			if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_1, 2) === 0 ? false : true)) {
				break lab41;
			}
			$this.bra = $this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		lab42 = true;
	lab42:
		while (lab42 === true) {
			lab42 = false;
			if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
				break lab42;
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		lab43 = true;
	lab43:
		while (lab43 === true) {
			lab43 = false;
			$this.ket = $this.cursor;
			lab44 = true;
		lab44:
			while (lab44 === true) {
				lab44 = false;
				v_22 = (($this.limit - $this.cursor) | 0);
				lab45 = true;
			lab45:
				while (lab45 === true) {
					lab45 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_6, 4) === 0 ? false : true)) {
						break lab45;
					}
					break lab44;
				}
				$this.cursor = (($this.limit - v_22) | 0);
				lab46 = true;
			lab46:
				while (lab46 === true) {
					lab46 = false;
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
						break lab46;
					}
					break lab44;
				}
				$this.cursor = (($this.limit - v_22) | 0);
				if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_4, 2) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_y_consonant$LTurkishStemmer$($this) ? false : true)) {
					break lab43;
				}
			}
			$this.bra = $this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
			v_23 = (($this.limit - $this.cursor) | 0);
			lab47 = true;
		lab47:
			while (lab47 === true) {
				lab47 = false;
				$this.ket = $this.cursor;
				lab48 = true;
			lab48:
				while (lab48 === true) {
					lab48 = false;
					v_24 = (($this.limit - $this.cursor) | 0);
					lab49 = true;
				lab49:
					while (lab49 === true) {
						lab49 = false;
						if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$($this) ? false : true)) {
							break lab49;
						}
						$this.bra = $this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						v_25 = (($this.limit - $this.cursor) | 0);
						lab50 = true;
					lab50:
						while (lab50 === true) {
							lab50 = false;
							$this.ket = $this.cursor;
							if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
								$this.cursor = (($this.limit - v_25) | 0);
								break lab50;
							}
						}
						break lab48;
					}
					$this.cursor = (($this.limit - v_24) | 0);
					if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
						$this.cursor = (($this.limit - v_23) | 0);
						break lab47;
					}
				}
				$this.bra = $this.cursor;
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
					return false;
				}
				$this.ket = $this.cursor;
				if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
					$this.cursor = (($this.limit - v_23) | 0);
					break lab47;
				}
			}
			break lab0;
		}
		cursor$1 = $this.cursor = (($this.limit - v_1) | 0);
		$this.ket = cursor$1;
		lab51 = true;
	lab51:
		while (lab51 === true) {
			lab51 = false;
			v_26 = (($this.limit - $this.cursor) | 0);
			lab52 = true;
		lab52:
			while (lab52 === true) {
				lab52 = false;
				if (! (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_0, 10) === 0 ? false : ! TurkishStemmer$r_mark_suffix_with_optional_U_vowel$LTurkishStemmer$($this) ? false : true)) {
					break lab52;
				}
				break lab51;
			}
			$this.cursor = (($this.limit - v_26) | 0);
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_U, 105, 305) ? false : ! TurkishStemmer$r_mark_suffix_with_optional_s_consonant$LTurkishStemmer$($this) ? false : true)) {
				return false;
			}
		}
		$this.bra = $this.cursor;
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		v_27 = (($this.limit - $this.cursor) | 0);
		lab53 = true;
	lab53:
		while (lab53 === true) {
			lab53 = false;
			$this.ket = $this.cursor;
			if (! (! TurkishStemmer$r_check_vowel_harmony$LTurkishStemmer$($this) ? false : BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_16, 2) === 0 ? false : true)) {
				$this.cursor = (($this.limit - v_27) | 0);
				break lab53;
			}
			$this.bra = $this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
			if (! TurkishStemmer$r_stem_suffix_chain_before_ki$LTurkishStemmer$($this)) {
				$this.cursor = (($this.limit - v_27) | 0);
				break lab53;
			}
		}
	}
	return true;
};

TurkishStemmer.r_stem_noun_suffixes$LTurkishStemmer$ = TurkishStemmer$r_stem_noun_suffixes$LTurkishStemmer$;

TurkishStemmer.prototype.r_post_process_last_consonants$ = function () {
	var among_var;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, TurkishStemmer.a_23, 4);
	if (among_var === 0) {
		return false;
	}
	this.bra = this.cursor;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "p")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "\u00E7")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "t")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "k")) {
			return false;
		}
		break;
	}
	return true;
};

TurkishStemmer.prototype.r_post_process_last_consonants = TurkishStemmer.prototype.r_post_process_last_consonants$;

function TurkishStemmer$r_post_process_last_consonants$LTurkishStemmer$($this) {
	var among_var;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, TurkishStemmer.a_23, 4);
	if (among_var === 0) {
		return false;
	}
	$this.bra = $this.cursor;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "p")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "\u00E7")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "t")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "k")) {
			return false;
		}
		break;
	}
	return true;
};

TurkishStemmer.r_post_process_last_consonants$LTurkishStemmer$ = TurkishStemmer$r_post_process_last_consonants$LTurkishStemmer$;

TurkishStemmer.prototype.r_append_U_to_stems_ending_with_d_or_g$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_9;
	var v_10;
	var v_11;
	var v_12;
	var v_13;
	var v_14;
	var v_15;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var lab5;
	var lab6;
	var lab7;
	var c;
	var lab8;
	var lab10;
	var lab11;
	var lab12;
	var lab13;
	var lab15;
	var lab16;
	var lab17;
	var lab19;
	var lab20;
	var lab21;
	var c_bra$0;
	var adjustment$0;
	var c_bra$1;
	var adjustment$1;
	var c_bra$2;
	var adjustment$2;
	var c_bra$3;
	var adjustment$3;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var cursor$3;
	var cursor$4;
	var cursor$5;
	var cursor$6;
	var limit$0;
	var cursor$7;
	var cursor$8;
	var $__jsx_postinc_t;
	v_1 = ((this.limit - this.cursor) | 0);
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_2 = ((this.limit - this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "d")) {
				break lab1;
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_2) | 0);
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "g")) {
			return false;
		}
	}
	this.cursor = ((this.limit - v_1) | 0);
	lab2 = true;
lab2:
	while (lab2 === true) {
		lab2 = false;
		v_3 = ((this.limit - this.cursor) | 0);
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			v_4 = ((this.limit - this.cursor) | 0);
		golab4:
			while (true) {
				v_5 = ((this.limit - this.cursor) | 0);
				lab5 = true;
			lab5:
				while (lab5 === true) {
					lab5 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel, 97, 305)) {
						break lab5;
					}
					this.cursor = ((this.limit - v_5) | 0);
					break golab4;
				}
				cursor$0 = this.cursor = ((this.limit - v_5) | 0);
				if (cursor$0 <= this.limit_backward) {
					break lab3;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			lab6 = true;
		lab6:
			while (lab6 === true) {
				lab6 = false;
				v_6 = ((this.limit - this.cursor) | 0);
				lab7 = true;
			lab7:
				while (lab7 === true) {
					lab7 = false;
					if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "a")) {
						break lab7;
					}
					break lab6;
				}
				this.cursor = ((this.limit - v_6) | 0);
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "\u0131")) {
					break lab3;
				}
			}
			cursor$1 = this.cursor = ((this.limit - v_4) | 0);
			c = cursor$1;
			c_bra$0 = cursor$1;
			adjustment$0 = BaseStemmer$replace_s$LBaseStemmer$IIS(this, cursor$1, cursor$1, "\u0131");
			if (cursor$1 <= this.bra) {
				this.bra = (this.bra + adjustment$0) | 0;
			}
			if (c_bra$0 <= this.ket) {
				this.ket = (this.ket + adjustment$0) | 0;
			}
			this.cursor = c;
			break lab2;
		}
		this.cursor = ((this.limit - v_3) | 0);
		lab8 = true;
	lab8:
		while (lab8 === true) {
			lab8 = false;
			v_7 = ((this.limit - this.cursor) | 0);
		golab9:
			while (true) {
				v_8 = ((this.limit - this.cursor) | 0);
				lab10 = true;
			lab10:
				while (lab10 === true) {
					lab10 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel, 97, 305)) {
						break lab10;
					}
					this.cursor = ((this.limit - v_8) | 0);
					break golab9;
				}
				cursor$2 = this.cursor = ((this.limit - v_8) | 0);
				if (cursor$2 <= this.limit_backward) {
					break lab8;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			lab11 = true;
		lab11:
			while (lab11 === true) {
				lab11 = false;
				v_9 = ((this.limit - this.cursor) | 0);
				lab12 = true;
			lab12:
				while (lab12 === true) {
					lab12 = false;
					if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "e")) {
						break lab12;
					}
					break lab11;
				}
				this.cursor = ((this.limit - v_9) | 0);
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "i")) {
					break lab8;
				}
			}
			cursor$3 = this.cursor = ((this.limit - v_7) | 0);
			c = cursor$3;
			c_bra$1 = cursor$3;
			adjustment$1 = BaseStemmer$replace_s$LBaseStemmer$IIS(this, cursor$3, cursor$3, "i");
			if (cursor$3 <= this.bra) {
				this.bra = (this.bra + adjustment$1) | 0;
			}
			if (c_bra$1 <= this.ket) {
				this.ket = (this.ket + adjustment$1) | 0;
			}
			this.cursor = c;
			break lab2;
		}
		this.cursor = ((this.limit - v_3) | 0);
		lab13 = true;
	lab13:
		while (lab13 === true) {
			lab13 = false;
			v_10 = ((this.limit - this.cursor) | 0);
		golab14:
			while (true) {
				v_11 = ((this.limit - this.cursor) | 0);
				lab15 = true;
			lab15:
				while (lab15 === true) {
					lab15 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel, 97, 305)) {
						break lab15;
					}
					this.cursor = ((this.limit - v_11) | 0);
					break golab14;
				}
				cursor$4 = this.cursor = ((this.limit - v_11) | 0);
				if (cursor$4 <= this.limit_backward) {
					break lab13;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			lab16 = true;
		lab16:
			while (lab16 === true) {
				lab16 = false;
				v_12 = ((this.limit - this.cursor) | 0);
				lab17 = true;
			lab17:
				while (lab17 === true) {
					lab17 = false;
					if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "o")) {
						break lab17;
					}
					break lab16;
				}
				this.cursor = ((this.limit - v_12) | 0);
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "u")) {
					break lab13;
				}
			}
			cursor$5 = this.cursor = ((this.limit - v_10) | 0);
			c = cursor$5;
			c_bra$2 = cursor$5;
			adjustment$2 = BaseStemmer$replace_s$LBaseStemmer$IIS(this, cursor$5, cursor$5, "u");
			if (cursor$5 <= this.bra) {
				this.bra = (this.bra + adjustment$2) | 0;
			}
			if (c_bra$2 <= this.ket) {
				this.ket = (this.ket + adjustment$2) | 0;
			}
			this.cursor = c;
			break lab2;
		}
		cursor$7 = this.cursor = (((limit$0 = this.limit) - v_3) | 0);
		v_13 = ((limit$0 - cursor$7) | 0);
	golab18:
		while (true) {
			v_14 = ((this.limit - this.cursor) | 0);
			lab19 = true;
		lab19:
			while (lab19 === true) {
				lab19 = false;
				if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel, 97, 305)) {
					break lab19;
				}
				this.cursor = ((this.limit - v_14) | 0);
				break golab18;
			}
			cursor$6 = this.cursor = ((this.limit - v_14) | 0);
			if (cursor$6 <= this.limit_backward) {
				return false;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		}
		lab20 = true;
	lab20:
		while (lab20 === true) {
			lab20 = false;
			v_15 = ((this.limit - this.cursor) | 0);
			lab21 = true;
		lab21:
			while (lab21 === true) {
				lab21 = false;
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "\u00F6")) {
					break lab21;
				}
				break lab20;
			}
			this.cursor = ((this.limit - v_15) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "\u00FC")) {
				return false;
			}
		}
		cursor$8 = this.cursor = ((this.limit - v_13) | 0);
		c = cursor$8;
		c_bra$3 = cursor$8;
		adjustment$3 = BaseStemmer$replace_s$LBaseStemmer$IIS(this, cursor$8, cursor$8, "\u00FC");
		if (cursor$8 <= this.bra) {
			this.bra = (this.bra + adjustment$3) | 0;
		}
		if (c_bra$3 <= this.ket) {
			this.ket = (this.ket + adjustment$3) | 0;
		}
		this.cursor = c;
	}
	return true;
};

TurkishStemmer.prototype.r_append_U_to_stems_ending_with_d_or_g = TurkishStemmer.prototype.r_append_U_to_stems_ending_with_d_or_g$;

function TurkishStemmer$r_append_U_to_stems_ending_with_d_or_g$LTurkishStemmer$($this) {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_9;
	var v_10;
	var v_11;
	var v_12;
	var v_13;
	var v_14;
	var v_15;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var lab5;
	var lab6;
	var lab7;
	var c;
	var lab8;
	var lab10;
	var lab11;
	var lab12;
	var lab13;
	var lab15;
	var lab16;
	var lab17;
	var lab19;
	var lab20;
	var lab21;
	var c_bra$0;
	var adjustment$0;
	var c_bra$1;
	var adjustment$1;
	var c_bra$2;
	var adjustment$2;
	var c_bra$3;
	var adjustment$3;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var cursor$3;
	var cursor$4;
	var cursor$5;
	var cursor$6;
	var limit$0;
	var cursor$7;
	var cursor$8;
	var $__jsx_postinc_t;
	v_1 = (($this.limit - $this.cursor) | 0);
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_2 = (($this.limit - $this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "d")) {
				break lab1;
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_2) | 0);
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "g")) {
			return false;
		}
	}
	$this.cursor = (($this.limit - v_1) | 0);
	lab2 = true;
lab2:
	while (lab2 === true) {
		lab2 = false;
		v_3 = (($this.limit - $this.cursor) | 0);
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			v_4 = (($this.limit - $this.cursor) | 0);
		golab4:
			while (true) {
				v_5 = (($this.limit - $this.cursor) | 0);
				lab5 = true;
			lab5:
				while (lab5 === true) {
					lab5 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel, 97, 305)) {
						break lab5;
					}
					$this.cursor = (($this.limit - v_5) | 0);
					break golab4;
				}
				cursor$0 = $this.cursor = (($this.limit - v_5) | 0);
				if (cursor$0 <= $this.limit_backward) {
					break lab3;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			lab6 = true;
		lab6:
			while (lab6 === true) {
				lab6 = false;
				v_6 = (($this.limit - $this.cursor) | 0);
				lab7 = true;
			lab7:
				while (lab7 === true) {
					lab7 = false;
					if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "a")) {
						break lab7;
					}
					break lab6;
				}
				$this.cursor = (($this.limit - v_6) | 0);
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "\u0131")) {
					break lab3;
				}
			}
			cursor$1 = $this.cursor = (($this.limit - v_4) | 0);
			c = cursor$1;
			c_bra$0 = cursor$1;
			adjustment$0 = BaseStemmer$replace_s$LBaseStemmer$IIS($this, cursor$1, cursor$1, "\u0131");
			if (cursor$1 <= $this.bra) {
				$this.bra = ($this.bra + adjustment$0) | 0;
			}
			if (c_bra$0 <= $this.ket) {
				$this.ket = ($this.ket + adjustment$0) | 0;
			}
			$this.cursor = c;
			break lab2;
		}
		$this.cursor = (($this.limit - v_3) | 0);
		lab8 = true;
	lab8:
		while (lab8 === true) {
			lab8 = false;
			v_7 = (($this.limit - $this.cursor) | 0);
		golab9:
			while (true) {
				v_8 = (($this.limit - $this.cursor) | 0);
				lab10 = true;
			lab10:
				while (lab10 === true) {
					lab10 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel, 97, 305)) {
						break lab10;
					}
					$this.cursor = (($this.limit - v_8) | 0);
					break golab9;
				}
				cursor$2 = $this.cursor = (($this.limit - v_8) | 0);
				if (cursor$2 <= $this.limit_backward) {
					break lab8;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			lab11 = true;
		lab11:
			while (lab11 === true) {
				lab11 = false;
				v_9 = (($this.limit - $this.cursor) | 0);
				lab12 = true;
			lab12:
				while (lab12 === true) {
					lab12 = false;
					if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "e")) {
						break lab12;
					}
					break lab11;
				}
				$this.cursor = (($this.limit - v_9) | 0);
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "i")) {
					break lab8;
				}
			}
			cursor$3 = $this.cursor = (($this.limit - v_7) | 0);
			c = cursor$3;
			c_bra$1 = cursor$3;
			adjustment$1 = BaseStemmer$replace_s$LBaseStemmer$IIS($this, cursor$3, cursor$3, "i");
			if (cursor$3 <= $this.bra) {
				$this.bra = ($this.bra + adjustment$1) | 0;
			}
			if (c_bra$1 <= $this.ket) {
				$this.ket = ($this.ket + adjustment$1) | 0;
			}
			$this.cursor = c;
			break lab2;
		}
		$this.cursor = (($this.limit - v_3) | 0);
		lab13 = true;
	lab13:
		while (lab13 === true) {
			lab13 = false;
			v_10 = (($this.limit - $this.cursor) | 0);
		golab14:
			while (true) {
				v_11 = (($this.limit - $this.cursor) | 0);
				lab15 = true;
			lab15:
				while (lab15 === true) {
					lab15 = false;
					if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel, 97, 305)) {
						break lab15;
					}
					$this.cursor = (($this.limit - v_11) | 0);
					break golab14;
				}
				cursor$4 = $this.cursor = (($this.limit - v_11) | 0);
				if (cursor$4 <= $this.limit_backward) {
					break lab13;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			}
			lab16 = true;
		lab16:
			while (lab16 === true) {
				lab16 = false;
				v_12 = (($this.limit - $this.cursor) | 0);
				lab17 = true;
			lab17:
				while (lab17 === true) {
					lab17 = false;
					if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "o")) {
						break lab17;
					}
					break lab16;
				}
				$this.cursor = (($this.limit - v_12) | 0);
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "u")) {
					break lab13;
				}
			}
			cursor$5 = $this.cursor = (($this.limit - v_10) | 0);
			c = cursor$5;
			c_bra$2 = cursor$5;
			adjustment$2 = BaseStemmer$replace_s$LBaseStemmer$IIS($this, cursor$5, cursor$5, "u");
			if (cursor$5 <= $this.bra) {
				$this.bra = ($this.bra + adjustment$2) | 0;
			}
			if (c_bra$2 <= $this.ket) {
				$this.ket = ($this.ket + adjustment$2) | 0;
			}
			$this.cursor = c;
			break lab2;
		}
		cursor$7 = $this.cursor = (((limit$0 = $this.limit) - v_3) | 0);
		v_13 = ((limit$0 - cursor$7) | 0);
	golab18:
		while (true) {
			v_14 = (($this.limit - $this.cursor) | 0);
			lab19 = true;
		lab19:
			while (lab19 === true) {
				lab19 = false;
				if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel, 97, 305)) {
					break lab19;
				}
				$this.cursor = (($this.limit - v_14) | 0);
				break golab18;
			}
			cursor$6 = $this.cursor = (($this.limit - v_14) | 0);
			if (cursor$6 <= $this.limit_backward) {
				return false;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		}
		lab20 = true;
	lab20:
		while (lab20 === true) {
			lab20 = false;
			v_15 = (($this.limit - $this.cursor) | 0);
			lab21 = true;
		lab21:
			while (lab21 === true) {
				lab21 = false;
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "\u00F6")) {
					break lab21;
				}
				break lab20;
			}
			$this.cursor = (($this.limit - v_15) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "\u00FC")) {
				return false;
			}
		}
		cursor$8 = $this.cursor = (($this.limit - v_13) | 0);
		c = cursor$8;
		c_bra$3 = cursor$8;
		adjustment$3 = BaseStemmer$replace_s$LBaseStemmer$IIS($this, cursor$8, cursor$8, "\u00FC");
		if (cursor$8 <= $this.bra) {
			$this.bra = ($this.bra + adjustment$3) | 0;
		}
		if (c_bra$3 <= $this.ket) {
			$this.ket = ($this.ket + adjustment$3) | 0;
		}
		$this.cursor = c;
	}
	return true;
};

TurkishStemmer.r_append_U_to_stems_ending_with_d_or_g$LTurkishStemmer$ = TurkishStemmer$r_append_U_to_stems_ending_with_d_or_g$LTurkishStemmer$;

TurkishStemmer.prototype.r_more_than_one_syllable_word$ = function () {
	var v_1;
	var v_3;
	var v_2;
	var lab1;
	var lab3;
	var $__jsx_postinc_t;
	v_1 = this.cursor;
	v_2 = 2;
replab0:
	while (true) {
		v_3 = this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
		golab2:
			while (true) {
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, TurkishStemmer.g_vowel, 97, 305)) {
						break lab3;
					}
					break golab2;
				}
				if (this.cursor >= this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
			v_2--;
			continue replab0;
		}
		this.cursor = v_3;
		break replab0;
	}
	if (v_2 > 0) {
		return false;
	}
	this.cursor = v_1;
	return true;
};

TurkishStemmer.prototype.r_more_than_one_syllable_word = TurkishStemmer.prototype.r_more_than_one_syllable_word$;

function TurkishStemmer$r_more_than_one_syllable_word$LTurkishStemmer$($this) {
	var v_1;
	var v_3;
	var v_2;
	var lab1;
	var lab3;
	var $__jsx_postinc_t;
	v_1 = $this.cursor;
	v_2 = 2;
replab0:
	while (true) {
		v_3 = $this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
		golab2:
			while (true) {
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, TurkishStemmer.g_vowel, 97, 305)) {
						break lab3;
					}
					break golab2;
				}
				if ($this.cursor >= $this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
			v_2--;
			continue replab0;
		}
		$this.cursor = v_3;
		break replab0;
	}
	if (v_2 > 0) {
		return false;
	}
	$this.cursor = v_1;
	return true;
};

TurkishStemmer.r_more_than_one_syllable_word$LTurkishStemmer$ = TurkishStemmer$r_more_than_one_syllable_word$LTurkishStemmer$;

TurkishStemmer.prototype.r_is_reserved_word$ = function () {
	var v_1;
	var v_2;
	var v_4;
	var lab0;
	var lab1;
	var lab3;
	var lab5;
	var I_strlen$0;
	var cursor$0;
	var I_strlen$1;
	var $__jsx_postinc_t;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_2 = this.cursor;
		golab2:
			while (true) {
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					if (! BaseStemmer$eq_s$LBaseStemmer$IS(this, 2, "ad")) {
						break lab3;
					}
					break golab2;
				}
				if (this.cursor >= this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
			I_strlen$0 = this.I_strlen = 2;
			if (! (I_strlen$0 === this.limit)) {
				break lab1;
			}
			this.cursor = v_2;
			break lab0;
		}
		cursor$0 = this.cursor = v_1;
		v_4 = cursor$0;
	golab4:
		while (true) {
			lab5 = true;
		lab5:
			while (lab5 === true) {
				lab5 = false;
				if (! BaseStemmer$eq_s$LBaseStemmer$IS(this, 5, "soyad")) {
					break lab5;
				}
				break golab4;
			}
			if (this.cursor >= this.limit) {
				return false;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
		I_strlen$1 = this.I_strlen = 5;
		if (! (I_strlen$1 === this.limit)) {
			return false;
		}
		this.cursor = v_4;
	}
	return true;
};

TurkishStemmer.prototype.r_is_reserved_word = TurkishStemmer.prototype.r_is_reserved_word$;

function TurkishStemmer$r_is_reserved_word$LTurkishStemmer$($this) {
	var v_1;
	var v_2;
	var v_4;
	var lab0;
	var lab1;
	var lab3;
	var lab5;
	var I_strlen$0;
	var cursor$0;
	var I_strlen$1;
	var $__jsx_postinc_t;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = $this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_2 = $this.cursor;
		golab2:
			while (true) {
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					if (! BaseStemmer$eq_s$LBaseStemmer$IS($this, 2, "ad")) {
						break lab3;
					}
					break golab2;
				}
				if ($this.cursor >= $this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
			I_strlen$0 = $this.I_strlen = 2;
			if (! (I_strlen$0 === $this.limit)) {
				break lab1;
			}
			$this.cursor = v_2;
			break lab0;
		}
		cursor$0 = $this.cursor = v_1;
		v_4 = cursor$0;
	golab4:
		while (true) {
			lab5 = true;
		lab5:
			while (lab5 === true) {
				lab5 = false;
				if (! BaseStemmer$eq_s$LBaseStemmer$IS($this, 5, "soyad")) {
					break lab5;
				}
				break golab4;
			}
			if ($this.cursor >= $this.limit) {
				return false;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
		I_strlen$1 = $this.I_strlen = 5;
		if (! (I_strlen$1 === $this.limit)) {
			return false;
		}
		$this.cursor = v_4;
	}
	return true;
};

TurkishStemmer.r_is_reserved_word$LTurkishStemmer$ = TurkishStemmer$r_is_reserved_word$LTurkishStemmer$;

TurkishStemmer.prototype.r_postlude$ = function () {
	var v_1;
	var v_2;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	var limit$0;
	var cursor$1;
	v_1 = this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		if (! TurkishStemmer$r_is_reserved_word$LTurkishStemmer$(this)) {
			break lab0;
		}
		return false;
	}
	cursor$0 = this.cursor = v_1;
	this.limit_backward = cursor$0;
	cursor$1 = this.cursor = limit$0 = this.limit;
	v_2 = ((limit$0 - cursor$1) | 0);
	lab1 = true;
lab1:
	while (lab1 === true) {
		lab1 = false;
		if (! TurkishStemmer$r_append_U_to_stems_ending_with_d_or_g$LTurkishStemmer$(this)) {
			break lab1;
		}
	}
	this.cursor = ((this.limit - v_2) | 0);
	lab2 = true;
lab2:
	while (lab2 === true) {
		lab2 = false;
		if (! TurkishStemmer$r_post_process_last_consonants$LTurkishStemmer$(this)) {
			break lab2;
		}
	}
	this.cursor = this.limit_backward;
	return true;
};

TurkishStemmer.prototype.r_postlude = TurkishStemmer.prototype.r_postlude$;

function TurkishStemmer$r_postlude$LTurkishStemmer$($this) {
	var v_1;
	var v_2;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	var limit$0;
	var cursor$1;
	v_1 = $this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		if (! TurkishStemmer$r_is_reserved_word$LTurkishStemmer$($this)) {
			break lab0;
		}
		return false;
	}
	cursor$0 = $this.cursor = v_1;
	$this.limit_backward = cursor$0;
	cursor$1 = $this.cursor = limit$0 = $this.limit;
	v_2 = ((limit$0 - cursor$1) | 0);
	lab1 = true;
lab1:
	while (lab1 === true) {
		lab1 = false;
		if (! TurkishStemmer$r_append_U_to_stems_ending_with_d_or_g$LTurkishStemmer$($this)) {
			break lab1;
		}
	}
	$this.cursor = (($this.limit - v_2) | 0);
	lab2 = true;
lab2:
	while (lab2 === true) {
		lab2 = false;
		if (! TurkishStemmer$r_post_process_last_consonants$LTurkishStemmer$($this)) {
			break lab2;
		}
	}
	$this.cursor = $this.limit_backward;
	return true;
};

TurkishStemmer.r_postlude$LTurkishStemmer$ = TurkishStemmer$r_postlude$LTurkishStemmer$;

TurkishStemmer.prototype.stem$ = function () {
	var v_1;
	var lab0;
	var lab1;
	var limit$0;
	var cursor$0;
	if (! TurkishStemmer$r_more_than_one_syllable_word$LTurkishStemmer$(this)) {
		return false;
	}
	this.limit_backward = this.cursor;
	cursor$0 = this.cursor = limit$0 = this.limit;
	v_1 = ((limit$0 - cursor$0) | 0);
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		if (! TurkishStemmer$r_stem_nominal_verb_suffixes$LTurkishStemmer$(this)) {
			break lab0;
		}
	}
	this.cursor = ((this.limit - v_1) | 0);
	if (! this.B_continue_stemming_noun_suffixes) {
		return false;
	}
	lab1 = true;
lab1:
	while (lab1 === true) {
		lab1 = false;
		if (! TurkishStemmer$r_stem_noun_suffixes$LTurkishStemmer$(this)) {
			break lab1;
		}
	}
	this.cursor = this.limit_backward;
	return (! TurkishStemmer$r_postlude$LTurkishStemmer$(this) ? false : true);
};

TurkishStemmer.prototype.stem = TurkishStemmer.prototype.stem$;

TurkishStemmer.prototype.equals$X = function (o) {
	return o instanceof TurkishStemmer;
};

TurkishStemmer.prototype.equals = TurkishStemmer.prototype.equals$X;

function TurkishStemmer$equals$LTurkishStemmer$X($this, o) {
	return o instanceof TurkishStemmer;
};

TurkishStemmer.equals$LTurkishStemmer$X = TurkishStemmer$equals$LTurkishStemmer$X;

TurkishStemmer.prototype.hashCode$ = function () {
	var classname;
	var hash;
	var i;
	var char;
	classname = "TurkishStemmer";
	hash = 0;
	for (i = 0; i < classname.length; i++) {
		char = classname.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash;
	}
	return (hash | 0);
};

TurkishStemmer.prototype.hashCode = TurkishStemmer.prototype.hashCode$;

function TurkishStemmer$hashCode$LTurkishStemmer$($this) {
	var classname;
	var hash;
	var i;
	var char;
	classname = "TurkishStemmer";
	hash = 0;
	for (i = 0; i < classname.length; i++) {
		char = classname.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash;
	}
	return (hash | 0);
};

TurkishStemmer.hashCode$LTurkishStemmer$ = TurkishStemmer$hashCode$LTurkishStemmer$;

TurkishStemmer.serialVersionUID = 1;
$__jsx_lazy_init(TurkishStemmer, "methodObject", function () {
	return new TurkishStemmer();
});
$__jsx_lazy_init(TurkishStemmer, "a_0", function () {
	return [ new Among("m", -1, -1), new Among("n", -1, -1), new Among("miz", -1, -1), new Among("niz", -1, -1), new Among("muz", -1, -1), new Among("nuz", -1, -1), new Among("m\u00FCz", -1, -1), new Among("n\u00FCz", -1, -1), new Among("m\u0131z", -1, -1), new Among("n\u0131z", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_1", function () {
	return [ new Among("leri", -1, -1), new Among("lar\u0131", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_2", function () {
	return [ new Among("ni", -1, -1), new Among("nu", -1, -1), new Among("n\u00FC", -1, -1), new Among("n\u0131", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_3", function () {
	return [ new Among("in", -1, -1), new Among("un", -1, -1), new Among("\u00FCn", -1, -1), new Among("\u0131n", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_4", function () {
	return [ new Among("a", -1, -1), new Among("e", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_5", function () {
	return [ new Among("na", -1, -1), new Among("ne", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_6", function () {
	return [ new Among("da", -1, -1), new Among("ta", -1, -1), new Among("de", -1, -1), new Among("te", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_7", function () {
	return [ new Among("nda", -1, -1), new Among("nde", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_8", function () {
	return [ new Among("dan", -1, -1), new Among("tan", -1, -1), new Among("den", -1, -1), new Among("ten", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_9", function () {
	return [ new Among("ndan", -1, -1), new Among("nden", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_10", function () {
	return [ new Among("la", -1, -1), new Among("le", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_11", function () {
	return [ new Among("ca", -1, -1), new Among("ce", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_12", function () {
	return [ new Among("im", -1, -1), new Among("um", -1, -1), new Among("\u00FCm", -1, -1), new Among("\u0131m", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_13", function () {
	return [ new Among("sin", -1, -1), new Among("sun", -1, -1), new Among("s\u00FCn", -1, -1), new Among("s\u0131n", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_14", function () {
	return [ new Among("iz", -1, -1), new Among("uz", -1, -1), new Among("\u00FCz", -1, -1), new Among("\u0131z", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_15", function () {
	return [ new Among("siniz", -1, -1), new Among("sunuz", -1, -1), new Among("s\u00FCn\u00FCz", -1, -1), new Among("s\u0131n\u0131z", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_16", function () {
	return [ new Among("lar", -1, -1), new Among("ler", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_17", function () {
	return [ new Among("niz", -1, -1), new Among("nuz", -1, -1), new Among("n\u00FCz", -1, -1), new Among("n\u0131z", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_18", function () {
	return [ new Among("dir", -1, -1), new Among("tir", -1, -1), new Among("dur", -1, -1), new Among("tur", -1, -1), new Among("d\u00FCr", -1, -1), new Among("t\u00FCr", -1, -1), new Among("d\u0131r", -1, -1), new Among("t\u0131r", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_19", function () {
	return [ new Among("cas\u0131na", -1, -1), new Among("cesine", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_20", function () {
	return [ new Among("di", -1, -1), new Among("ti", -1, -1), new Among("dik", -1, -1), new Among("tik", -1, -1), new Among("duk", -1, -1), new Among("tuk", -1, -1), new Among("d\u00FCk", -1, -1), new Among("t\u00FCk", -1, -1), new Among("d\u0131k", -1, -1), new Among("t\u0131k", -1, -1), new Among("dim", -1, -1), new Among("tim", -1, -1), new Among("dum", -1, -1), new Among("tum", -1, -1), new Among("d\u00FCm", -1, -1), new Among("t\u00FCm", -1, -1), new Among("d\u0131m", -1, -1), new Among("t\u0131m", -1, -1), new Among("din", -1, -1), new Among("tin", -1, -1), new Among("dun", -1, -1), new Among("tun", -1, -1), new Among("d\u00FCn", -1, -1), new Among("t\u00FCn", -1, -1), new Among("d\u0131n", -1, -1), new Among("t\u0131n", -1, -1), new Among("du", -1, -1), new Among("tu", -1, -1), new Among("d\u00FC", -1, -1), new Among("t\u00FC", -1, -1), new Among("d\u0131", -1, -1), new Among("t\u0131", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_21", function () {
	return [ new Among("sa", -1, -1), new Among("se", -1, -1), new Among("sak", -1, -1), new Among("sek", -1, -1), new Among("sam", -1, -1), new Among("sem", -1, -1), new Among("san", -1, -1), new Among("sen", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_22", function () {
	return [ new Among("mi\u015F", -1, -1), new Among("mu\u015F", -1, -1), new Among("m\u00FC\u015F", -1, -1), new Among("m\u0131\u015F", -1, -1) ];
});
$__jsx_lazy_init(TurkishStemmer, "a_23", function () {
	return [ new Among("b", -1, 1), new Among("c", -1, 2), new Among("d", -1, 3), new Among("\u011F", -1, 4) ];
});
TurkishStemmer.g_vowel = [ 17, 65, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 32, 8, 0, 0, 0, 0, 0, 0, 1 ];
TurkishStemmer.g_U = [ 1, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0, 0, 0, 0, 1 ];
TurkishStemmer.g_vowel1 = [ 1, 64, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1 ];
TurkishStemmer.g_vowel2 = [ 17, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 130 ];
TurkishStemmer.g_vowel3 = [ 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1 ];
TurkishStemmer.g_vowel4 = [ 17 ];
TurkishStemmer.g_vowel5 = [ 65 ];
TurkishStemmer.g_vowel6 = [ 65 ];

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
	"src/turkish-stemmer.jsx": {
		TurkishStemmer: TurkishStemmer,
		TurkishStemmer$: TurkishStemmer
	}
};


})(JSX);

var Among = JSX.require("src/among.jsx").Among;
var Among$SII = JSX.require("src/among.jsx").Among$SII;
var Stemmer = JSX.require("src/stemmer.jsx").Stemmer;
var BaseStemmer = JSX.require("src/base-stemmer.jsx").BaseStemmer;
var TurkishStemmer = JSX.require("src/turkish-stemmer.jsx").TurkishStemmer;
