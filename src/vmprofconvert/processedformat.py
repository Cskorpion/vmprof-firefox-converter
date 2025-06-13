class InvalidFormatException(Exception):
    pass

def check_processed_profile(prof):
    if "meta" not in prof:
        raise InvalidFormatException("meta key missing")
    else:
        check_meta(prof["meta"])
    if "libs" not in prof:
        raise InvalidFormatException("libs key missing")
    if "pages" not in prof:
        raise InvalidFormatException("pages key missing")
    if "counters" in prof and len(prof["counters"]) != 0:
        check_counters(prof["counters"])
    if "threads" not in prof:
        raise InvalidFormatException("threads key missing")
    else:
        check_threads(prof["threads"])

def check_meta(meta):
    if "interval" not in meta:
        raise InvalidFormatException("interval key missing")
    if "startTime" not in meta:
        raise InvalidFormatException("startTime key missing")
    if "abi" not in meta:
        raise InvalidFormatException("abi key missing")
    if "oscpu" not in meta:
        raise InvalidFormatException("oscpu key missing")
    if "platform" not in meta:
        raise InvalidFormatException("platform key missing")
    if "processType" not in meta:
        raise InvalidFormatException("processType key missing")
    if "stackwalk" not in meta:
        raise InvalidFormatException("stackwalk key missing")
    if "debug" not in meta:
        raise InvalidFormatException("debug key missing")
    if "version" not in meta:
        raise InvalidFormatException("version key missing")
    if "categories" not in meta:
        raise InvalidFormatException("categories key missing")
    if "preprocessedProfileVersion" not in meta:
        raise InvalidFormatException("preprocessedProfileVersion key missing")
    if "symbolicated" not in meta:
        raise InvalidFormatException("symbolicated key missing")
    if "markerSchema" not in meta:
        raise InvalidFormatException("markerSchema key missing")
   

def check_counters(counters):
    for counter in counters:
        if "name" not in counter:
            raise InvalidFormatException("name key missing")
        if "category" not in counter:
            raise InvalidFormatException("category key missing")
        if "description" not in counter:
            raise InvalidFormatException("description key missing")
        if "pid" not in counter:
            raise InvalidFormatException("pid key missing")
        if "mainThreadIndex" not in counter:
            raise InvalidFormatException("mainThreadIndex key missing")
        if "sampleGroups" not in counter:
            raise InvalidFormatException("sampleGroups key missing")
        else:
            check_samplegroups(counter["sampleGroups"])

def check_samplegroups(samplegroups):
    for samplegroup in samplegroups:
        if "id" not in samplegroup:
            raise InvalidFormatException("sampleGroups id key missing")
        if "samples" not in samplegroup:
            raise InvalidFormatException("sampleGroups samples key missing")
        else:
            if "length" not in samplegroup["samples"]:
                raise InvalidFormatException("sampleGroups length key missing")
            if "time" not in samplegroup["samples"]:
                raise InvalidFormatException("sampleGroups time key missing")
            if "count" not in samplegroup["samples"]:
                raise InvalidFormatException("sampleGroups count key missing")
        
def check_threads(threads):
    for thread in threads:
        if "name" not in thread:
            raise InvalidFormatException("name key missing")
        if "isMainThread" not in thread:
            raise InvalidFormatException("isMainThread key missing")
        if "processType" not in thread:
            raise InvalidFormatException("processType key missing")
        if "processName" not in thread:
            raise InvalidFormatException("processName key missing")
        if "processStartupTime" not in thread:
            raise InvalidFormatException("processStartupTime key missing")
        if "processShutdownTime" not in thread:
            raise InvalidFormatException("processShutdownTime key missing")
        if "registerTime" not in thread:
            raise InvalidFormatException("registerTime key missing")
        if "unregisterTime" not in thread:
            raise InvalidFormatException("unregisterTime key missing")
        if "tid" not in thread:
            raise InvalidFormatException("tid key missing")
        if "pid" not in thread:
            raise InvalidFormatException("pid key missing")
        if "markers" not in thread:
            raise InvalidFormatException("markers key missing")
        else:
            check_markers(thread["markers"])
        if "frameTable" not in thread:
            raise InvalidFormatException("frameTable key missing")
        else:
            check_frametable(thread["frameTable"])
        if "funcTable" not in thread:
            raise InvalidFormatException("funcTable key missing")
        else:
            check_functable(thread["funcTable"])
        if "resourceTable" not in thread:
            raise InvalidFormatException("resourceTable key missing")
        else:
            check_resourcetable(thread["resourceTable"])
        if "stackTable" not in thread:
            raise InvalidFormatException("stackTable key missing")
        else:
            check_stacktable(thread["stackTable"])
        if "samples" not in thread:
            raise InvalidFormatException("samples key missing")
        else:
            check_samples(thread["samples"])
        if "stringArray" not in thread:
            raise InvalidFormatException("stringArray key missing")
        
def check_markers(markers):
    if "data" not in markers:
        raise InvalidFormatException("markers type key missing")
    if "length" not in markers:
        raise InvalidFormatException("markers length key missing")
        
def check_frametable(frametable):
    if "address" not in frametable:
        raise InvalidFormatException("frametable address key missing")
    if "inlineDepth" not in frametable:
        raise InvalidFormatException("frametable inlineDepth key missing")
    if "category" not in frametable:
        raise InvalidFormatException("frametable category key missing")
    if "subcategory" not in frametable:
        raise InvalidFormatException("frametable subcategory key missing")
    if "func" not in frametable:
        raise InvalidFormatException("frametable func key missing")
    if "innerWindowID" not in frametable:
        raise InvalidFormatException("frametable innerWindowID key missing")
    if "length" not in frametable:
        raise InvalidFormatException("frametable length key missing")
        
def check_functable(functable):
    if "isJS" not in functable:
        raise InvalidFormatException("functable isJS key missing")
    if "relevantForJS" not in functable:
        raise InvalidFormatException("functable relevantForJS key missing")
    if "name" not in functable:
        raise InvalidFormatException("functable name key missing")
    if "resource" not in functable:
        raise InvalidFormatException("functable resource key missing")
    if "fileName" not in functable:
        raise InvalidFormatException("functable fileName key missing")
    if "lineNumber" not in functable:
        raise InvalidFormatException("functable lineNumber key missing")
    if "columnNumber" not in functable:
        raise InvalidFormatException("functable columnNumber key missing")
    if "length" not in functable:
        raise InvalidFormatException("functable length key missing")
    
def check_resourcetable(resourcetable):
    if "type" not in resourcetable:
        raise InvalidFormatException("resourcetable type key missing")
    if "length" not in resourcetable:
        raise InvalidFormatException("resourcetable length key missing")

def check_stacktable(stacktable):
    if "frame" not in stacktable:
        raise InvalidFormatException("stacktable frame key missing")
    if "category" not in stacktable:
        raise InvalidFormatException("stacktable category key missing")
    if "subcategory" not in stacktable:
        raise InvalidFormatException("stacktable subcategory key missing")
    if "prefix" not in stacktable:
        raise InvalidFormatException("stacktable prefix key missing")
    if "length" not in stacktable:
        raise InvalidFormatException("stacktable length key missing")
    
def check_samples(samples):
    if "stack" not in samples:
        raise InvalidFormatException("samples stack key missing")
    if "time" not in samples:
        raise InvalidFormatException("samples time key missing")
    if "eventDelay" not in samples:
        raise InvalidFormatException("samples eventDelay key missing")
    if "weightType" not in samples:
        raise InvalidFormatException("samples weightType key missing")
    if "weight" not in samples:
        raise InvalidFormatException("samples weight key missing")
    if "length" not in samples:
        raise InvalidFormatException("samples length key missing")