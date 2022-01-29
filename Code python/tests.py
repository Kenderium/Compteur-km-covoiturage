import _thread
import time

compteur_km = True

def second_thread():         # Seconde tâche
    global compteur_km
    while compteur_km:
        baton.acquire()      # Regarde si le thread est libre et se l'acquière
        
        print("okthread1")
        time.sleep(5)        # Pendant 5 secs (pour les tests)
        compteur_km = False
        print("okthread2")
        baton.release()      # Libère le thread

baton = _thread.allocate_lock()               # Bloqueur de thread pour éviter crash,...
_thread.start_new_thread(second_thread, ())   # Création du thread et démarrage

print("okmain1")
time.sleep(5)        # Pendant 5 secs (pour les tests)
print("okmain2")
