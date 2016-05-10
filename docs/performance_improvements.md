Possible performance improvements --- Learner's side
====================================================

Testing method
--------------

I created a test course, with a work group containing three students, and then; 

* Profiled page loading time. 
* Manually counted `/api/server` calls from both Apros and GWv2. 
 
My findings are: 

1. Natural thing to look for performance improvements would be to reduce number of API calls, which come with 
   some TCP and HTTP overhead. However whole GWv2 -> LMS communication is done using a localhost address, which 
   should have very small overhead. While we should profile and reduce API calls, they shouldn't be main problem. 
2. Number of API calls from Apros and GWv2 is *roughly the same*, with Apros making slightly more calls (also makes 
   calls to similar endpoints) so most probably there is limited possibility of making significant performance leaps 
   here.
3. On my devstack most of time wait time was due to each navigation step triggered full page reload, which reloaded 
   Apros Page, and when that page was loaded initiated Ajax request to download GWv2 contents. 
4. On my devstack scripts loaded from XBlock were not not cached, need to double-check if this is also the case 
   in production environment (I suspect that this is not the case!), hovewer if it is the case this would be the 
   lowest hanging fruit to fix. 

Recommendations
---------------

1. If project navigation used ajax to load stage selected by user we would cut page load roughly in half --- there would 
   be no round-trip to Apros. This would be a majorish project though.

 
    
   
 