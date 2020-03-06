/************************* MAIN() ***********************************/
#include <stdio.h>
#include <math.h>
#include <stdlib.h>


/*  Linear equation solver for lamp crosstalk */

#define BUFFER 1.e-5

void 
main ( int argc, char **argv )
{
    float *pa[4],x[4],b[7],o[7],e[7] ;
    int rp[4];
    int n = 4;
    float ma[16];
    FILE *fp;
    int k;
    void linsolv();

    for (k=0; k < 7; k++){
        b[k] = atof(argv[k+1]);
        o[k] = b[k];  /* original values; b is destroyed by linsolv */
    }

#if 0
    printf("\n%6.3f %6.3f %6.3f %6.3f %6.3f %6.3f %6.3f\n",
        b[0],b[1],b[2],b[3],b[4],b[5],b[6]);
    printf("\n%6.3f %6.3f %6.3f %6.3f %6.3f %6.3f %6.3f\n\n",
        o[0],o[1],o[2],o[3],o[4],o[5],o[6]);
#endif
      
    /* make matrix pointers */
    for (k=0; k < 4; k++) pa[k] = ma + 4*k ;
    
    /* get the matrix and expected brightness vector */
    fp=fopen("/usr/local/bin/crosstable.dat","r");
    for (k=0; k < 4; k++){
        fscanf(fp,"%f %f %f %f",pa[k],pa[k]+1,pa[k]+2,pa[k]+3);
    /*printf("%6.3f %6.3f %6.3f %6.3f\n",pa[k][0],pa[k][1],pa[k][2],pa[k][3]);*/
    }
    fscanf(fp,"%f %f %f %f %f %f %f",e,e+1,e+2,e+3,e+4,e+5,e+6);

#if 0    
    printf("%6.3f %6.3f %6.3f %6.3f %6.3f %6.3f %6.3f\n",
        e[0],e[1],e[2],e[3],e[4],e[5],e[6]); 
#endif
    
    fclose(fp);

    /* do the solution */

    linsolv(pa,b,x,4);

    for( k=0; k < 4; k++ ){
        /* if( x[k] < 0.03 && o[k] < 0.03 ) x[k] = o[k]; */
        if(o[k] < 0.04 || x[k] < 0.04) x[k] = 0.;
        printf("%6.2f ",fabs(x[k]/e[k])) ;
    }
    for( k=4; k < 7; k++){
        if(o[k] < .04) o[k] = 0.0;
        printf("%6.2f ", o[k]/e[k]) ;
    }
    putchar('\n') ;
    
}


/*********************** AFAMAX() **************************************/
/*
 * returns absolute max of float array a, pointer to index of max element
 * in pj
 */
double
afamax(a, n, pj)
float *a ;
register int n ;
int *pj ;
{
    int j= 0 ;
    register int i ;
    float b,c ;


    b = 0. ;
    for (i=0 ; i < n ; i++ ) {
        if((c = fabs(*(a+i))) > b) {
            b=c ;
            j=i ;
        }
    }
    *pj = j ;
    return b ;
}



/************************* LINSOLV() ***********************************/
/*  Linear equation solver. Solves pa[i][j]*x[j] = b[i] */
/* This thing ALSO destroys pa, but it does not matter here, bcz it
/* is read at each invocation. */

#define BUFFER 1.e-5
extern double afamax() ;

void 
linsolv(pa,b,x,n)
float *pa[],b[],x[] ;
int n ;
{
    float sc[4];
    int rp[4];
    float am, c, m, akk, r ;
    int im, i, j, k, rpi, it ;
    
    for( k = 0 ; k < n ; k++) {
        rp[k] = k ;  /* initialize row ptrs */
        sc[k] = afamax( pa[k], n, &im ) ; /* scale facs=max row elts */
    }
    for( k = 0 ; k < n ; k++) {
        /* first find max abs scaled element in col k, row >= k */
        am = 0. ;
        for ( i = k ; i < n ; i++ ) {
            rpi = rp[i] ;
            c = fabs(*(*(pa+rpi)+k))/sc[rpi] ;
            if(c > am ){
                am = c ;
                im = i ;
            }
        }
        it = rp[im] ;
        rp[im] = rp[k] ;
        rp[k] = it ;
        akk = *(*(pa + it) + k ) ;
        for ( i = k+1 ; i < n ; i++ ) {
            rpi = rp[i] ;
            m = (*(*(pa + rpi) + k ) =  *(*(pa + rpi)+k)/akk) ;
            for( j = k + 1 ; j < n ; j++ ){
                *(*(pa + rpi)+j) -= m * (*(*(pa + it) + j )) ;
            }
            b[rpi] -= m * b[it] ;
        }
    }
    for( i = n-1 ; i >= 0 ; i--) {
        rpi = rp[i] ;
        r = b[rpi] ;
        for ( j = i + 1 ; j <n ; j++ ) r -= (*(*(pa + rpi)+j))*x[j] ;
        if ( fabs((m=(*(*(pa+rpi)+i)))) > BUFFER*sc[rpi] ){
            x[i] = r/m ;
        }else if( r < BUFFER*sc[rpi] ){
            puts("\nmatrix singular, system consistent\n");
            x[i] = 0. ;
        }else{
            puts("\nmatrix singular");
        }
    }
}

