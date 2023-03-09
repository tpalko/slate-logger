## patches 

### local StreamHandler

diff --git a/src/cowpy/__init__.py b/src/cowpy/__init__.py
index 97f847f..180a3c9 100644
--- a/src/cowpy/__init__.py
+++ b/src/cowpy/__init__.py
@@ -10,3 +10,4 @@ cs = Cowpy()
 # print('--------  Finished Instantiating Cowpy   ------------')
 
 getLogger = cs.getLogger
+StreamHandler = logging.StreamHandler
