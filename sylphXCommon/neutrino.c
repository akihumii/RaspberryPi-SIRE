/**
 * @file    neutrino-parallel.c
 * @author  Shih Chiang Liu
 * @date    12 June 2018
 * @version 0.1
 * @brief  A Loadable Kernel Module that controls Neutrino's Parallel Interface at full speed from kernel space.
 */
#include <linux/module.h>		/* Needed by all modules */
#include <linux/kernel.h>		/* Needed for KERN_INFO */
#include <linux/init.h>			/* Needed for the macros */
#include <linux/kthread.h>		/* Needed for kernel thread */
#include <linux/gpio.h>			/* Needed for the GPIO */
#include <linux/interrupt.h>	/* Needed for interrupt handler */
#include <linux/delay.h>		/* Needed for scheduling */
#include <linux/sched.h>
#include <linux/signal.h>

///< The license type -- this affects runtime behavior
MODULE_LICENSE("GPL");

///< The author -- visible when you use modinfo
MODULE_AUTHOR("Shih Chiang Liu");

///< The description -- see modinfo
MODULE_DESCRIPTION("Neutrino Parallel Interface!");

///< The version of the module
MODULE_VERSION("0.1");

/* GPIO */

#define CTS		27
#define RESET		22
#define DATA_RDY	17
#define BIT7		21
#define BIT6		20
#define BIT5		16
#define BIT4		12
#define BIT3		25
#define BIT2		24
#define BIT1		23
#define BIT0		18

#define BUFFER_SIZE 4096

static void nara_gpio_init(void){
	gpio_request(DATA_RDY, "DATA_RDY");
	gpio_direction_input(DATA_RDY);
	gpio_set_debounce(DATA_RDY, 20);
	gpio_export(DATA_RDY, false);

	gpio_request(CTS, "CTS");
	gpio_request(RESET, "RESET");

	gpio_direction_output(CTS, 1);
	gpio_direction_output(RESET, 0);

	gpio_export(CTS, false);
	gpio_export(RESET, false);

	gpio_request(BIT7, "BIT7");
	gpio_request(BIT6, "BIT6");
	gpio_request(BIT5, "BIT5");
	gpio_request(BIT4, "BIT4");
	gpio_request(BIT3, "BIT3");
	gpio_request(BIT2, "BIT2");
	gpio_request(BIT1, "BIT1");
	gpio_request(BIT0, "BIT0");

	gpio_direction_input(BIT7);
	gpio_direction_input(BIT6);
	gpio_direction_input(BIT5);
	gpio_direction_input(BIT4);
	gpio_direction_input(BIT3);
	gpio_direction_input(BIT2);
	gpio_direction_input(BIT1);
	gpio_direction_input(BIT0);

	gpio_export(BIT7, false);
	gpio_export(BIT6, false);
	gpio_export(BIT5, false);
	gpio_export(BIT4, false);
	gpio_export(BIT3, false);
	gpio_export(BIT2, false);
	gpio_export(BIT1, false);
	gpio_export(BIT0, false);

	printk(KERN_INFO "DATA_RDY current state: %d\n", gpio_get_value(DATA_RDY));
}

static void nara_gpio_exit(void){
	gpio_set_value(CTS, 0);
	gpio_set_value(RESET, 0);
	gpio_unexport(CTS);
	gpio_unexport(RESET);

	gpio_free(CTS);
	gpio_free(RESET);

	gpio_unexport(BIT7);
	gpio_unexport(BIT6);
	gpio_unexport(BIT5);
	gpio_unexport(BIT4);
	gpio_unexport(BIT3);
	gpio_unexport(BIT2);
	gpio_unexport(BIT1);
	gpio_unexport(BIT0);

	gpio_free(BIT7);
	gpio_free(BIT6);
	gpio_free(BIT5);
	gpio_free(BIT4);
	gpio_free(BIT3);
	gpio_free(BIT2);
	gpio_free(BIT1);
	gpio_free(BIT0);

	gpio_unexport(DATA_RDY);
	gpio_free(DATA_RDY);
}

/* SYSFS */

static struct kobject *nara_kobject;
static char foo[BUFFER_SIZE];
static int foo_index = 0;
static char byte;

static ssize_t show_nara(struct kobject *kobj, struct kobj_attribute *attr, char *buf){
	sprintf(buf, "%s\n", foo);
	memset(foo, '\0', foo_index);
	foo_index = 0;
	return 0;
}

static ssize_t store_nara(struct kobject *kobj, struct kobj_attribute *attr, const char *buf, size_t count){
	return 0;
}

static struct kobj_attribute nara_attribute =__ATTR(nara, (S_IRUSR | S_IRUGO), show_nara, store_nara);

static void nara_sysfs_init(void){
	printk(KERN_INFO "nara: starting sysfs...");
	nara_kobject = kobject_create_and_add("nara", NULL);
	if (sysfs_create_file(nara_kobject, &nara_attribute.attr)) {
		printk(KERN_INFO "failed to create nara sysfs!\n");
	}
	printk(KERN_INFO "nara: starting sysfs done.");
}

static void nara_sysfs_exit(void){
	printk(KERN_INFO "nara: stopping sysfs...");
	kobject_put(nara_kobject);
	printk(KERN_INFO "nara: stopping sysfs done.");
}

/* THREAD */

#define THREAD_PRIORITY	45
#define THREAD_NAME	"nara" //Shortform for Neutrino Parallel Thread

static struct task_struct *task;

static int nara_thread(void *data){
	allow_signal(SIGKILL);
	gpio_set_value(RESET, 1);
	while(!kthread_should_stop()){
		set_current_state(TASK_RUNNING);       // prevent inadvertent sleeps temporarily (just an example)
		gpio_set_value(CTS, 1);
		while(!gpio_get_value(DATA_RDY));
		if(gpio_get_value(DATA_RDY)){
			foo[foo_index] = (unsigned char) gpio_get_value(BIT7) << 7 | 
				(unsigned char) gpio_get_value(BIT6) << 6 |
				(unsigned char) gpio_get_value(BIT5) << 5 | 
				(unsigned char) gpio_get_value(BIT4) << 4 |
				(unsigned char) gpio_get_value(BIT3) << 3 |
				(unsigned char) gpio_get_value(BIT2) << 2 |
				(unsigned char) gpio_get_value(BIT1) << 1 |
				(unsigned char) gpio_get_value(BIT0);
//			printk(KERN_INFO "Size of foo: %d \n", sizeof(foo));					
//			printk(KERN_INFO "Current byte value : %d \n", foo[foo_index]);
			if(foo_index < (BUFFER_SIZE - 1)){
			       	foo_index++;
			}
			else{
				foo_index = 0;
//				printk(KERN_INFO "Nara Buffer full \n");
			}
			gpio_set_value(CTS, 0);
			while(gpio_get_value(DATA_RDY));
		}
//		gpio_set_value(CTS, 1);
		set_current_state(TASK_INTERRUPTIBLE); // going to sleep but can be awoken if required
	}
	return 0;
}
static void nara_thread_init(void){
	printk(KERN_INFO "nara: starting thread...");
	task = kthread_run(nara_thread, NULL, THREAD_NAME);
	printk(KERN_INFO "nara: starting thread done.");
}

static void nara_thread_exit(void){
	printk(KERN_INFO "nara: stopping thread...");
	kthread_stop(task);
	printk(KERN_INFO "nara: stopping thread done.");
}

/* MODULE */

static int __init neutrino_start(void){
	printk(KERN_INFO "Loading Neutrino Kernel module...\n");
	nara_sysfs_init();
	nara_gpio_init();
	nara_thread_init();
	printk(KERN_INFO "Neutrino Kernel module loaded! \n");
	return 0;
}

static void __exit neutrino_end(void){
	printk(KERN_INFO "Stopping Neutrino Kernel module \n");
	nara_sysfs_exit();
	nara_gpio_exit();
	nara_thread_exit();
	printk(KERN_INFO "Neutrino Kernel module removed! \n");
}

module_init(neutrino_start);
module_exit(neutrino_end);
