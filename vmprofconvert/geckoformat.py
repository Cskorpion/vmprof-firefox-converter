class InvalidFormatException(Exception):
    pass

def check_gecko_profile(prof):
    if "meta" not in prof:
        raise InvalidFormatException("meta key missing")
    else:
        check_meta(prof["meta"])
    if "pages" not in prof:
        raise InvalidFormatException("pages key missing")
    if "libs" not in prof:
        raise InvalidFormatException("libs key missing")
    if "pausedRanges" not in prof:
        raise InvalidFormatException("pausedRanges key missing")
    if "threads" not in prof:
        raise InvalidFormatException("threads key missing")
    else:
        check_threads(prof["threads"])
    if "processes" not in prof:
        raise InvalidFormatException("processes key missing")

def check_meta(meta):
    if "version" not in meta:
        raise InvalidFormatException("version key missing")
    if "interval" not in meta:
        raise InvalidFormatException("interval key missing")
    if "stackwalk" not in meta:
        raise InvalidFormatException("stackwalk key missing")
    if "debug" not in meta:
        raise InvalidFormatException("debug key missing")
    if "startTime" not in meta:
        raise InvalidFormatException("startTime key missing")
    if "shutdownTime" not in meta:
        raise InvalidFormatException("stackwalk key missing")
    if "processType" not in meta:
        raise InvalidFormatException("processType key missing")
    if "platform" not in meta:
        raise InvalidFormatException("platform key missing")
    if "oscpu" not in meta:
        raise InvalidFormatException("oscpu key missing")
    if "abi" not in meta:
        raise InvalidFormatException("abi key missing")
    
def check_threads(threads):
    for thread in threads:
        if "name" not in thread:
            raise InvalidFormatException("name key missing")
        if "processType" not in thread:
            raise InvalidFormatException("processType key missing")
        if "processName" not in thread:
            raise InvalidFormatException("processName key missing")
        if "tid" not in thread:
            raise InvalidFormatException("tid key missing")
        if "pid" not in thread:
            raise InvalidFormatException("pid key missing")
        if "registerTime" not in thread:
            raise InvalidFormatException("registerTime key missing")
        if "unregisterTime" not in thread:
            raise InvalidFormatException("unregisterTime key missing")
        if "markers" not in thread:
            raise InvalidFormatException("markers key missing")
        else:
            check_markers(thread["markers"])
        if "samples" not in thread:
            raise InvalidFormatException("samples key missing")
        else:
            check_samples(thread["samples"])
        if "frameTable" not in thread:
            raise InvalidFormatException("frameTable key missing")
        else:
            check_frametable(thread["frameTable"])
        if "stackTable" not in thread:
            raise InvalidFormatException("stackTable key missing")
        else:
            check_stacktable(thread["stackTable"])
        if "stringTable" not in thread:
            raise InvalidFormatException("stringTable key missing")

def check_markers(markers):
    if "schema" not in markers:
        raise InvalidFormatException("schema key missing")
    else:
        check_marker_schema(markers["schema"])
    if "data" not in markers:
        raise InvalidFormatException("data key missing")
        
def check_marker_schema(schema):
    if "name" not in schema:
        raise InvalidFormatException("name key missing")
    if "time" not in schema:
        raise InvalidFormatException("time key missing")
    if "data" not in schema:
        raise InvalidFormatException("data key missing")
    
def check_samples(samples):
    if "schema" not in samples:
        raise InvalidFormatException("samples schema key missing")
    else:
        check_samples_schema(samples["schema"])
    if "data" not in samples:
        raise InvalidFormatException("samples data key missing")

def check_frametable(frametable):
    if "schema" not in frametable:
        raise InvalidFormatException("frameTable schema key missing")
    else:
        check_frametable_schema(frametable["schema"])
    if "data" not in frametable:
        raise InvalidFormatException("frameTable data key missing")

def check_stacktable(stacktable):
    if "schema" not in stacktable:
        raise InvalidFormatException("stackTable schema key missing")
    else:
        check_stacktable_schema(stacktable["schema"])
    if "data" not in stacktable:
        raise InvalidFormatException("stackTable data key missing")
    
def check_samples_schema(schema):
    if "stack" not in schema:
        raise InvalidFormatException("samples stack key missing")
    if "time" not in schema:
        raise InvalidFormatException("samples time key missing")
    if "eventDelay" not in schema:
        raise InvalidFormatException("samples eventDelay key missing")
    
def check_frametable_schema(schema):
    if "location" not in schema:
        raise InvalidFormatException("frameTable location key missing")
    if "relevantForJS" not in schema:
        raise InvalidFormatException("frameTable relevantForJS key missing")
    if "innerWindowID" not in schema:
        raise InvalidFormatException("frameTable innerWindowID key missing")
    if "implementation" not in schema:
        raise InvalidFormatException("frameTable implementation key missing")
    
def check_stacktable_schema(schema):
    if "frame" not in schema:
        raise InvalidFormatException("stackTable frame key missing")
    if "prefix" not in schema:
        raise InvalidFormatException("stackTable prefix key missing")