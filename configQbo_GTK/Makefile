LIBS=`pkg-config --cflags --libs gtk+-3.0` -export-dynamic -lyaml
CC=gcc

all:configQbo

configQbo:configQbo.c yamlConfig.c
	$(CC) -Wall -g configQbo.c yamlConfig.c -o configQbo -I $(LIBS)

clean:
	-rm configQbo
