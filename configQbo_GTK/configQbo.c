
// gcc -o configQbo configQbo.c `pkg-config --cflags --libs gtk+-3.0` -export-dynamic
#define _GNU_SOURCE     /* To get defns of NI_MAXSERV and NI_MAXHOST */
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netdb.h>
#include <ifaddrs.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <linux/if_link.h>
#include <gtk/gtk.h>
#include "yamlConfig.h"

typedef struct ips {
  char name[20];
  char addr[20];
}ips;

YAMLconfig conf;

void printf_conf(void)
{
  printf("READ: age: %d, lang:%s, startWith: %s, token: %s, op_question: %s, volume: %d\n", conf.age, conf.language, conf.startWith, conf.tokenAPIai, conf.op_question, conf.volume);
  
}


int getIps(ips Ips[10])
{
  struct ifaddrs *ifaddr, *ifa;
  int family, s, n, nIps=0;
  char host[NI_MAXHOST];

  if (getifaddrs(&ifaddr) == -1) {
    perror("getifaddrs");
    exit(EXIT_FAILURE);
  }

  /* Walk through linked list, maintaining head pointer so we
     can free list later */

  for (ifa = ifaddr, n = 0; ifa != NULL; ifa = ifa->ifa_next, n++) {
    if (ifa->ifa_addr == NULL)
      continue;

    family = ifa->ifa_addr->sa_family;

    /* Display interface name and family (including symbolic
       form of the latter for the common families) */

    /*    printf("%-8s %s (%d)\n",
	   ifa->ifa_name,
	   (family == AF_PACKET) ? "AF_PACKET" :
	   (family == AF_INET) ? "AF_INET" :
	   (family == AF_INET6) ? "AF_INET6" : "???",
	   family);
    */
    /* For an AF_INET* interface address, display the address */

    if (family == AF_INET /* || family == AF_INET6*/) {
      s = getnameinfo(ifa->ifa_addr,
		      (family == AF_INET) ? sizeof(struct sockaddr_in) :
		      sizeof(struct sockaddr_in6),
		      host, NI_MAXHOST,
		      NULL, 0, NI_NUMERICHOST);
      if (s != 0) {
	printf("getnameinfo() failed: %s\n", gai_strerror(s));
	exit(EXIT_FAILURE);
      }

      //printf("\t\taddress: <%s>\n", host);
      sprintf(Ips[nIps].name,"%s", ifa->ifa_name);
      sprintf(Ips[nIps++].addr,"%s", host);
    }
  }

  freeifaddrs(ifaddr);
  return(nIps);
}

void on_butt_exit_clicked (GtkButton *button, gpointer   user_data)
{
  int dlgresponse;
    
  dlgresponse = gtk_dialog_run(GTK_DIALOG(user_data));
  
  if (dlgresponse == 1) {
    gtk_main_quit();
  }
  else if (dlgresponse == 0) {
    printf("Save changes dialog.\n");
    printf_conf();
    //    printf("CONF: age: %d, lang:%s, start: %s, token: %s.\n", conf.age, conf.language, conf.startWith, conf.tokenAPIai);
    writeConfig(&conf);
    gtk_main_quit();
  }
  else if (dlgresponse == 2) {

  }
  gtk_widget_hide(GTK_WIDGET(user_data));
}


void on_check_enableQuestions_toggled (GtkToggleButton *togglebutton, gpointer user_data)
{
  if ( gtk_toggle_button_get_active(togglebutton) ) {
    sprintf(conf.op_question, "yes"); 
  }
  else {
    sprintf(conf.op_question, "no"); 
  }
}


void on_butt_saveChanges_clicked (GtkButton *button, gpointer   user_data)
{

}


void on_combo_lang_changed(GtkComboBox *widget, gpointer user_data)
{
  gint idx;

  idx = gtk_combo_box_get_active (widget);
  printf("comboLan idx: %d\n", idx);
  switch (idx) {
  case 0:
    sprintf(conf.language, "english"); 
    break;
  case 1:
    sprintf(conf.language, "spanish"); 
    break;
  default:
    break;
  }
}

void on_combo_startWith_changed(GtkComboBox *widget, gpointer toggleOpQuestion)
{
  gint idx;

  idx = gtk_combo_box_get_active (widget);
  //printf("comboLan idx: %d\n", idx);
  switch (idx) {
  case 0:
    sprintf(conf.startWith, "scratch"); 
    gtk_widget_hide( GTK_WIDGET(toggleOpQuestion));
    break;
  case 1:
    sprintf(conf.startWith, "interactive-dialogflow"); 
    gtk_widget_show( GTK_WIDGET(toggleOpQuestion));
    break;
  case 2:
    sprintf(conf.startWith, "interactive-gassistant");
    gtk_widget_show( GTK_WIDGET(toggleOpQuestion));
  default:
    break;
  }
}

void on_entry_Token_changed(GtkEntry *entry, gpointer   user_data)
{
  //printf("entry changed: %s\n", gtk_entry_get_text (entry));
  sprintf(conf.tokenAPIai, "%s", gtk_entry_get_text (entry));
}

void onAssistantTokenChange(GtkEntry *entry, gpointer   user_data)
{
  sprintf(conf.gassistant_proyectid, "%s", gtk_entry_get_text (entry));
}


void on_adjustment_volume_value_changed (GtkAdjustment *adjustment, gpointer       user_data)
{
  conf.volume = (int)gtk_adjustment_get_value(adjustment);
}


int main(int argc, char *argv[])
{
  GtkBuilder *builder; 
  GtkWidget *window;
  GtkLabel *ipLocal;
  GtkLabel *ipEthernet;
  GtkLabel *ipWifi;
  GtkComboBox *comboStartWith;
  GtkComboBox *comboLanguage;
  GtkEntry *entryToken;
 GtkEntry *entryTokenAssistant;
  GtkToggleButton *toggleOpQuestion;
  GtkAdjustment *adjVolume;
  ips Ips[10];
  int nIps, i;

  
  readConfig(&conf);
  printf_conf();
  
  gtk_init(&argc, &argv);
 
  builder = gtk_builder_new();
  gtk_builder_add_from_file (builder, "/home/pi/Documents/configQbo_GTK/configQbo.glade", NULL);
 
  window = GTK_WIDGET(gtk_builder_get_object(builder, "window_main"));
  gtk_builder_connect_signals(builder, NULL);

  // update toggle op_question content
  toggleOpQuestion = GTK_TOGGLE_BUTTON(gtk_builder_get_object(builder, "check_enableQuestions"));
  if (strcmp(conf.op_question, "yes") == 0) {
    gtk_toggle_button_set_active  (GTK_TOGGLE_BUTTON(toggleOpQuestion), TRUE);
  }
  else {
    gtk_toggle_button_set_active  (GTK_TOGGLE_BUTTON(toggleOpQuestion), FALSE);
  }
  
  // update combo startWith content
  comboStartWith = GTK_COMBO_BOX(gtk_builder_get_object(builder, "combo_startWith"));
  if (strcmp(conf.startWith, "scratch") == 0) {
    gtk_combo_box_set_active (GTK_COMBO_BOX(comboStartWith), 0);
    gtk_widget_hide( GTK_WIDGET(toggleOpQuestion));
  }
  else if (strcmp(conf.startWith, "interactive-dialogflow") == 0) {
    gtk_combo_box_set_active (GTK_COMBO_BOX(comboStartWith), 1);
    gtk_widget_show( GTK_WIDGET(toggleOpQuestion));
  }
  else {
    gtk_combo_box_set_active (GTK_COMBO_BOX(comboStartWith), 2);
    gtk_widget_show( GTK_WIDGET(toggleOpQuestion));
  }

  // update combo language content
  comboLanguage = GTK_COMBO_BOX(gtk_builder_get_object(builder, "combo_lang"));
  if (strcmp(conf.language, "english") == 0) {
    gtk_combo_box_set_active (GTK_COMBO_BOX(comboLanguage), 0);
  }
  else if (strcmp(conf.language, "spanish") == 0) {
    gtk_combo_box_set_active (GTK_COMBO_BOX(comboLanguage), 1);
  }

  // Update volume adjustment
  adjVolume = GTK_ADJUSTMENT(gtk_builder_get_object(builder, "adjustment_volume"));
  gtk_adjustment_set_value (adjVolume, (gdouble)conf.volume);
  
  // update TokenAPIai entry
  entryToken = GTK_ENTRY(gtk_builder_get_object(builder, "entry_Token"));
  gtk_entry_set_text (entryToken, conf.tokenAPIai);
  
  // update assistant entry
  entryTokenAssistant = GTK_ENTRY(gtk_builder_get_object(builder, "entryTokenAssistant"));
  gtk_entry_set_text (entryTokenAssistant, conf.gassistant_proyectid);
  
  // geting Ip
  ipLocal = GTK_LABEL(gtk_builder_get_object(builder, "label_localIp"));
  ipEthernet = GTK_LABEL(gtk_builder_get_object(builder, "label_ethernetIp"));
  ipWifi = GTK_LABEL(gtk_builder_get_object(builder, "label_wifiIp"));

  nIps = getIps(Ips);
  //printf("nIps: %d\n", nIps);
  for (i=0; i<nIps; i++) {
    switch (Ips[i].name[0]) {
    case 'l':
      gtk_label_set_text (ipLocal, Ips[i].addr);
      break;
    case 'e':
      gtk_label_set_text (ipEthernet, Ips[i].addr);
      break;
    case 'w':
      gtk_label_set_text (ipWifi, Ips[i].addr);
      break;
    default:
      break;
    }
    //printf("%s: %s\n", Ips[i].name, Ips[i].addr);
  }
  
  g_object_unref(builder);
 
  gtk_widget_show(window);                
  gtk_main();
 
  return 0;
}
 
// called when window is closed
void on_window_main_destroy()
{
  gtk_main_quit();
}
