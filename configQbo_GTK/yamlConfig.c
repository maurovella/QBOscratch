#include <stdio.h>
#include <yaml.h>
#include "yamlConfig.h"

int readConfig(YAMLconfig* conf)
{
  FILE *fh = fopen("/home/pi/Documents/config.yml", "r");
  yaml_parser_t parser;
  yaml_token_t  token; 
  char key[256], value[256];
  
  // initialize conf struct
  memset(conf, 0, sizeof(YAMLconfig));
  
  /* Initialize parser */
  if(!yaml_parser_initialize(&parser))
    fputs("Failed to initialize parser!\n", stderr);
  if(fh == NULL)
    fputs("Failed to open file!\n", stderr);

  /* Set input file */
  yaml_parser_set_input_file(&parser, fh);


  /* CODE HERE */
  do {
    yaml_parser_scan(&parser, &token);
    switch(token.type)
      {
	/* Stream start/end */
	//      case YAML_STREAM_START_TOKEN: puts("STREAM START"); break;
	// case YAML_STREAM_END_TOKEN:   puts("STREAM END");   break;
	/* Token types (read before actual token) */
      case YAML_KEY_TOKEN:
	yaml_parser_scan(&parser, &token);
	sprintf(key,"%s", token.data.scalar.value);
	yaml_parser_scan(&parser, &token);
	yaml_parser_scan(&parser, &token);
	if (token.data.scalar.value == NULL)
	  break;
	sprintf(value,"%s", token.data.scalar.value);
	if (strcmp(key,"language") == 0) sprintf(conf->language, "%s", value);
	else if (strcmp(key,"startWith") == 0) sprintf(conf->startWith, "%s", value);
	else if (strcmp(key,"age") == 0) conf->age = atoi(value);
	else if (strcmp(key,"tokenAPIai") == 0) sprintf(conf->tokenAPIai, "%s", value);
        else if (strcmp(key,"gassistant_proyectid") == 0) sprintf(conf->gassistant_proyectid, "%s", value);
	else if (strcmp(key,"op_question") == 0) sprintf(conf->op_question, "%s", value);
	else if (strcmp(key,"volume") == 0) conf->volume = atoi(value);

	break;
	/*
      case YAML_VALUE_TOKEN:
	yaml_parser_scan(&parser, &token);
	printf("(Value token) %s \n", token.data.scalar.value);
	break;
	// Block delimeters 
      case YAML_BLOCK_SEQUENCE_START_TOKEN: puts("<b>Start Block (Sequence)</b>"); break;
      case YAML_BLOCK_ENTRY_TOKEN:          puts("<b>Start Block (Entry)</b>");    break;
      case YAML_BLOCK_END_TOKEN:            puts("<b>End block</b>");              break;
	// Data 
      case YAML_BLOCK_MAPPING_START_TOKEN:  puts("[Block mapping]");            break;
      case YAML_SCALAR_TOKEN:  printf("scalar %s \n", token.data.scalar.value); break;
	*/
	// Others 
      default:
	//	printf("Got token of type %d\n", token.type);
	break;
      }
    if(token.type != YAML_STREAM_END_TOKEN)
      yaml_token_delete(&token);
  } while(token.type != YAML_STREAM_END_TOKEN);
  yaml_token_delete(&token);
  
  /* Cleanup */
  yaml_parser_delete(&parser);
  fclose(fh);
  return 0;
}

int writeConfig(YAMLconfig* conf)
{
  FILE *fh = fopen("/home/pi/Documents/config.yml", "w");
 
  fprintf(fh, "{age: %d, language: %s, startWith: %s, tokenAPIai: %s, op_question: %s, volume: %d, gassistant_proyectid: %s}\n", conf->age, conf->language, conf->startWith, conf->tokenAPIai, conf->op_question, conf->volume, conf->gassistant_proyectid);
  fclose(fh);

  return 0;
}
