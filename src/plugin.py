'''
Created on Aug 7, 2010

@author: pedro
'''
import inspect, logging
import xbmcgui #@UnresolvedImport
from utils import pluginsupport

log = logging.getLogger("plugin")

class PluginResult:
  def __init__(self, size, items):
    self.size = size
    self.items = items

class PluginMovieItem:
  """An item resolved by a plugin. 
  Can be a link to a list of items or a playable item."""
  __listItem = None
  def __init__(self, name, url, mode=None, extraArgs=None):
    """Create an item 
    @param name: the name for this item
    @param url: the url to load this item
    @param mode: the mode for this link """
    self.name = name
    self.url = url
    self.mode = mode or "ROOT"
    self.extraArgs = extraArgs
    
  def getLabels(self):
    return { "title": self.name }
    
  def isPlayable(self):
    return modeHandlers[self.mode].playable
    
  def getTitle(self):
    return self.name
  
  def getPath(self):
    return self.url
  
  def buildContextMenu(self):
    pass
  
  def hasCover(self):
    return False;
  
  def getCover(self):
    return "";

  def hasFanart(self):
    return False;

  def getFanart(self):
    pass;
    
  def getListItem(self):
    """Create a list item for XBMC for this PluginMovieItem 
    @return the list item for XBMC"""
    if self.__listItem: 
      return self.__listItem

    thumb = ""
    if self.hasCover():
      thumb = pluginsupport._preChacheThumbnail(self.getCover(), "Loading cover for : '%s'" % self.name)

    self.__listItem = xbmcgui.ListItem(self.getTitle(), iconImage=thumb, thumbnailImage=thumb, path=self.getPath())
    self.__listItem.setInfo(type="Video", infoLabels=self.getLabels())

    if self.hasFanart():
      fanart = pluginsupport._preChacheThumbnail(self.getFanart(), "Loading fanart for : '%s'" % self.name)
      self.__listItem.setProperty('fanart_image', fanart)

    if self.isPlayable():
      self.__listItem.setProperty('IsPlayable', 'true')
      
    contextMenu = self.buildContextMenu()
    if contextMenu: 
      self.__listItem.addContextMenuItems(contextMenu)
    
    return self.__listItem
     
  def getTargetUrl(self, action=None, extra=None):
    """Returns the url for this item to use by XBMC
    @param action: optional action to add to the url"""
    extra = extra or self.extraArgs
    if self.mode:
      argsMap = {"url": self.url, "mode": str(self.mode), "name": self.name}
      if action:
        argsMap['action'] = action
      if extra:
        for key, value in extra.iteritems():
          argsMap[key] = value
      return pluginsupport.encode(argsMap)
    return self.url 


"""A registry of mode handlers"""
modeHandlers = {}
actionHandlers = {}
normalFlowActions = []

def mode(modeId, contentType=None, playable=False):
  """Decorator to register mode handler functions
  @param modeId: the mode to register the function for
  @param contentType: the content type this handler's generates
  @param playable: if the content is playable"""
  def decorate(function):
    log.debug("registering mode %r with content %r" % (modeId, contentType))
    modeHandlers[modeId] = HandlerWrapper(function, contentType, playable)
  return decorate

def root():
  """Decorator to register the root handler functions"""
  def decorate(function):
    log.debug("registering root")
    modeHandlers['ROOT'] = HandlerWrapper(function)
  return decorate

def action(actionId, normalFlow=False):
  """Decorator to register action handler functions
  @param actionId: the action to register the function for
  @param normalFlow: if this action should run like a normal flow action"""
  def decorate(function):
    actionHandlers[actionId] = HandlerWrapper(function)
    if normalFlow == True:
      normalFlowActions.append(actionId)
  return decorate

def __isAction(arguments):
  """Checks if a request is an action request
  @param arguments: the invocation arguments from XBMC
  @return true if this is an action request, false otherwise"""
  return arguments.has_key('action') and arguments['action'] not in normalFlowActions

def handle():
  """Handle an XBMC plugin request.
  This will get the appropriate handler function, execute it to get a PluginResult
  then if they-re in normal flor, handle the result by either listing the items or playing them.""" 
  arguments = pluginsupport.getArguments()
  def __getArgument(arg):
    if not arguments.has_key(arg): 
      return None
    val = arguments[arg]
    del arguments[arg]
    return val

  if __isAction(arguments):
    action = __getArgument('action')
    actionHandlers[action].call(arguments)
  else:
    mode = __getArgument('mode') or "ROOT"
    handler = modeHandlers[mode]
    result = handler.call(arguments)
    if handler.playable:
      pluginsupport.play(result.items)
    else:
      pluginsupport.list(result, handler.getContentType(arguments))
    pluginsupport.done()
    
class HandlerWrapper:
  """A wrapper for handler functions that can map arguments from XBMC's request
  to the handler functions parameters"""
  def __init__(self, handler, contentType=None, playable=False):
    """Creates a new wrapper for a handler function
    @param handler: the function to wrap
    @param contentType: the content type this handler generates
    @param playable: if the content is playable"""
    self.handlerFunction = handler
    self.contentType = contentType
    self.playable = playable
    
  def call(self, params={}):
    """Invokes the handler function
    @param params: the invocation params from XBMC
    @return: the result of the invocation of the handler function"""
    return _executeOne(self.handlerFunction, params)
  
  def getContentType(self, params):
    """Gets the content type for this handler
    @param params: the invocation params
    @return: the content type of this handler"""
    contentType = self.contentType
    if callable(contentType):
      contentType = contentType(params)
    return contentType

def __mapArgs(functionArgs, pluginParams):
  '''Map the plugins invocation arguments to the handler function arguments
  The arguments are matched by name
  @param functionArgs: The list of arguments the function requires
  @param pluginParams: the available params from the invocation of the plugin (url)
  @return: a dict of arguments to invoke the handler function with'''
  args = {}
  for arg in functionArgs:
    if pluginParams.has_key(arg):
      args[arg] = pluginParams[arg]
  return args

def _executeOne(f, params={}):
  """Execute a function with some params from the plugin
  This method maps the url encoded params into the mode handler function's arguments 
  and then invokes the handler function
  @param params the request params"""
  fargs = inspect.getargspec(f)[0]
  if not fargs:
    return f()
  log.debug("Function has args: %s" % str(fargs)) 
  args = __mapArgs(fargs, params)
  log.debug("Dispatching call to function with args: %s" % str(args)) 
  return f(**args)

